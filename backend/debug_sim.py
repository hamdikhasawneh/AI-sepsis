import sys
import os

# Add parent dir to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.simulation_service import simulation_service

try:
    print("Attempting to load data...")
    simulation_service.load_data()
    if simulation_service.static_data is not None:
        print("Data loaded! Cases:", simulation_service.static_data['case_name'].unique().tolist())
    else:
        print("Data is None!")
except Exception as e:
    import traceback
    print("Error loading data:")
    traceback.print_exc()
