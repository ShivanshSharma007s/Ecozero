from flask import Flask, render_template, request
import google.generativeai as genai
from collections import OrderedDict

app = Flask(__name__)

# Configure Gemini API
genai.configure(api_key='(Private)')
model = genai.GenerativeModel('gemini-1.5-flash')

def calculate_carbon_emissions(data):
    # Extract all relevant data
    electricity_units = float(data.get('electricity_units', 0))
    area = float(data.get('area', 1))
    occupants = int(data.get('occupants', 1))
    
    # HVAC factors
    hvac_type = data.get('hvac_system', 'None')
    hvac_star_rating = int(data.get('hvac_star_rating', 1))
    hvac_tonnage = float(data.get('hvac_tonnage', 0))
    
    # Building envelope factors
    wall_type = data.get('wall_assembly', 'Unknown')
    roof_type = data.get('roof_assembly', 'Unknown')
    window_type = data.get('window_glass', 'Unknown')
    
    # Appliance list
    appliances = request.form.getlist('appliances')
    other_appliances = data.get('other_appliances', '').split(',')
    all_appliances = appliances + [a.strip() for a in other_appliances if a.strip()]
    
    # Base electricity emissions (kg per kWh)
    electricity_factor = 0.5
    
    # HVAC adjustment factors
    hvac_factors = {
        'Fan': 0.1,
        'Split AC': 1.5 - (0.2 * hvac_star_rating),
        'Window AC': 1.8 - (0.2 * hvac_star_rating),
        'VRF': 2.0 - (0.15 * hvac_star_rating),
        'Chiller': 2.5 - (0.1 * hvac_star_rating)
    }
    hvac_adjustment = hvac_factors.get(hvac_type, 1.0) * max(hvac_tonnage, 0.1)
    
    # Building envelope adjustments
    envelope_factors = {
        'wall': {
            'Red Brick Construction': 1.2,
            'Concrete Block': 1.1,
            'Insulated Wall': 0.8
        },
        'roof': {
            'Reinforced Brick Concrete (RBC)': 1.3,
            'Insulated Roof': 0.7
        },
        'window': {
            'Single Glazed Unit (SGU)': 1.4,
            'Double Glazed Unit (DGU)': 0.8
        }
    }
    
    wall_factor = envelope_factors['wall'].get(wall_type, 1.0)
    roof_factor = envelope_factors['roof'].get(roof_type, 1.0)
    window_factor = envelope_factors['window'].get(window_type, 1.0)
    
    # Appliance adjustments
    appliance_factors = {
        'Air Conditioner': 1.5,
        'Refrigerator': 0.8,
        'Washing Machine': 0.5,
        'Geyser': 1.2,
        'Television': 0.3,
        'Computer': 0.4,
    }
    
    appliance_adjustment = 1.0
    for appliance in all_appliances:
        appliance_adjustment += appliance_factors.get(appliance, 0.1)
    
    # Calculate total emissions
    base_emissions = electricity_units * electricity_factor
    adjusted_emissions = (base_emissions * hvac_adjustment * wall_factor * 
                         roof_factor * window_factor * appliance_adjustment)
    
    # Normalize by area and occupants
    emissions_per_sqm = adjusted_emissions / area if area > 0 else adjusted_emissions
    emissions_per_capita = adjusted_emissions / occupants if occupants > 0 else adjusted_emissions
    
    # Calculate cost in rupees (₹0.50 per kgCO2)
    cost_in_rupees = adjusted_emissions * 0.5
    
    # Calculate annual electricity cost (assuming ₹6 per kWh as average rate)
    electricity_rate = 6  # ₹ per kWh
    annual_electricity_cost = electricity_units * electricity_rate
    
    # Calculate emission breakdown percentages
    hvac_contribution = base_emissions * (hvac_adjustment - 1)
    appliance_contribution = base_emissions * (appliance_adjustment - 1)
    envelope_contribution = base_emissions * (wall_factor * roof_factor * window_factor - 1)
    
    total = base_emissions + hvac_contribution + appliance_contribution + envelope_contribution
    
    emission_breakdown = OrderedDict([
        ('HVAC System', max(0, round((hvac_contribution / total) * 100, 1))),
        ('Appliances', max(0, round((appliance_contribution / total) * 100, 1))),
        ('Building Envelope', max(0, round((envelope_contribution / total) * 100, 1))),
        ('Base Electricity', max(0, round((base_emissions / total) * 100, 1)))
    ])
    
    # Projection data (5 years)
    projections = {
        'labels': ['Current', 'Year 1', 'Year 2', 'Year 3', 'Year 4', 'Year 5'],
        'emissions': [round(x, 1) for x in [
            adjusted_emissions,
            adjusted_emissions * 0.75,
            adjusted_emissions * 0.5,
            adjusted_emissions * 0.3,
            adjusted_emissions * 0.1,
            0
        ]],
        'savings': [round(x, 1) for x in [
            0,
            cost_in_rupees * 0.25,
            cost_in_rupees * 0.5,
            cost_in_rupees * 0.7,
            cost_in_rupees * 0.9,
            cost_in_rupees
        ]]
    }
    
    return (
        round(adjusted_emissions, 2), 
        round(emissions_per_sqm, 2), 
        round(emissions_per_capita, 2),
        round(cost_in_rupees, 2),
        round(annual_electricity_cost, 2),
        emission_breakdown,
        projections
    )

def get_netzero_recommendations(building_data, emissions, cost_in_rupees):
    prompt = f"""
    Building Details:
    - Name: {building_data.get('flat_name', 'Not specified')}
    - Type: {building_data.get('accommodation_type', 'Not specified')}
    - Area: {building_data.get('area', 0)} sqm
    - Climate: {building_data.get('climate_zone', 'Not specified')}
    - Current emissions: {emissions} kgCO2/year
    - Environmental cost: ₹{cost_in_rupees}/year
    - Annual Electricity: {building_data.get('electricity_units', 0)} kWh
    - Current Electricity Bill: ₹{building_data.get('electricity_bill', 0)}/year

    Provide detailed recommendations to achieve net-zero emissions with financial analysis in the following format:

    <div style='color: #27ae60; font-weight: bold; font-size: 1.2em; margin-bottom: 10px;'>Total Potential Annual Savings: ₹{cost_in_rupees + float(building_data.get('electricity_bill', 0))}</div>
    
    <div style='margin-bottom: 20px;'>This includes ₹{cost_in_rupees} in environmental costs and ₹{building_data.get('electricity_bill', 0)} in electricity bills that would be eliminated by achieving net-zero status.</div>

    <div style='color: #e74c3c; font-weight: bold; margin-top: 15px;'>1. Immediate Low-Cost Improvements:</div>
    <div style='margin-left: 20px; margin-bottom: 15px;'>
    Provide 2-3 specific low-cost improvements with their estimated costs, annual savings, and payback periods.
    </div>

    <div style='color: #e74c3c; font-weight: bold; margin-top: 15px;'>2. Medium-Term Upgrades:</div>
    <div style='margin-left: 20px; margin-bottom: 15px;'>
    Provide 2-3 medium-term upgrades with their typical Indian market costs and energy savings projections.
    </div>

    <div style='color: #e74c3c; font-weight: bold; margin-top: 15px;'>3. Renewable Energy Solutions:</div>
    <div style='margin-left: 20px; margin-bottom: 15px;'>
    Provide specific renewable energy solutions tailored to the building's characteristics.
    </div>

    <div style='color: #e74c3c; font-weight: bold; margin-top: 15px;'>4. Long-Term Financial Outlook:</div>
    <div style='margin-left: 20px;'>
    Provide a 5-year and 10-year projection of cumulative savings.
    </div>

    Make sure all numbers are in INR and all recommendations are specific to Indian context.
    """
    
    response = model.generate_content(prompt)
    return response.text

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        building_data = {
            'flat_name': request.form.get('flat_name'),
            'accommodation_type': request.form.get('accommodation_type'),
            'address': request.form.get('address'),
            'floors': request.form.get('floors'),
            'floor': request.form.get('floor'),
            'occupants': request.form.get('occupants'),
            'area': request.form.get('area'),
            'category': request.form.get('category'),
            'climate_zone': request.form.get('climate_zone'),
            'orientation': request.form.get('orientation'),
            'electricity_units': request.form.get('electricity_units'),
            'electricity_bill': request.form.get('electricity_bill'),
            'hvac_system': request.form.get('hvac_system'),
            'hvac_star_rating': request.form.get('hvac_star_rating'),
            'thermal_setpoint': request.form.get('thermal_setpoint'),
            'hvac_tonnage': request.form.get('hvac_tonnage'),
            'appliances': request.form.getlist('appliances'),
            'other_appliances': request.form.get('other_appliances'),
            'wall_area': request.form.get('wall_area'),
            'wall_assembly': request.form.get('wall_assembly'),
            'wall_insulation': request.form.get('wall_insulation'),
            'wall_tiles': request.form.get('wall_tiles'),
            'roof_area': request.form.get('roof_area'),
            'roof_assembly': request.form.get('roof_assembly'),
            'roof_insulation': request.form.get('roof_insulation'),
            'roof_tiles': request.form.get('roof_tiles'),
            'floor_area': request.form.get('floor_area'),
            'floor_assembly': request.form.get('floor_assembly'),
            'window_area': request.form.get('window_area'),
            'window_glass': request.form.get('window_glass'),
            'window_frame': request.form.get('window_frame'),
        }
        
        (total_emissions, per_sqm, per_capita, cost_in_rupees, 
         annual_electricity_cost, emission_breakdown, 
         projections) = calculate_carbon_emissions(building_data)
         
        recommendations = get_netzero_recommendations(building_data, total_emissions, cost_in_rupees)
        
        return render_template('result.html', 
                            emissions=total_emissions,
                            per_sqm=per_sqm,
                            per_capita=per_capita,
                            cost_in_rupees=cost_in_rupees,
                            annual_electricity_cost=annual_electricity_cost,
                            emission_breakdown=emission_breakdown,
                            projections=projections,
                            recommendations=recommendations,
                            building_data=building_data)
    
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
