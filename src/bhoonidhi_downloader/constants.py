BASE_URL = "https://bhoonidhi.nrsc.gov.in"
session_info = {"jwt": None,"userId": None, "user_email": None, "username": None, 'sid': None, 'scenes': []}

satellite_sensor_map = {
    # ResourceSat-1
    'RS1': {
        "LISS3": "ResourceSat-1_LISS3",
        "LISS4": "ResourceSat-1_LISS4(MONO)"
    },
    # ResourceSat-2
    'RS2': {
        "LISS3": ["ResourceSat-2_LISS3", "ResourceSat-2_LISS3_BOA", "ResourceSat-2_LISS3_L2"],
        "LISS4": ["ResourceSat-2_LISS4(MX23)", "ResourceSat-2_LISS4(MX70)", "ResourceSat-2_LISS4(MX70)_L2"]
    },
    # ResourceSat-2A
    'RS2A': {
        "LISS3": ["ResourceSat-2A_LISS3", "ResourceSat-2A_LISS3_BOA", "ResourceSat-2A_LISS3_L2"],
        "LISS4": ["ResourceSat-2A_LISS4(MX23)", "ResourceSat-2A_LISS4(MX70)", "ResourceSat-2A_LISS4(MX70)_L2"]
    },
    # Sentinel-2A
    'S2A': {
        "MSI": ["Sentinel-2A_MSI_Level-1C", "Sentinel-2A_MSI_Level-2A"]
    },
    # Sentinel-2B
    'S2B': {
        "MSI": ["Sentinel-2B_MSI_Level-1C", "Sentinel-2B_MSI_Level-2A"]
    },
    # IRS-1C
    'IRS1C': {
        "PAN": ["IRS-1C_PAN"]
    },
    # IRS-1D
    'IRS1D': {
        "PAN": ["IRS-1D_PAN"],
        "LISS3": ["IRS-1D_LISS3"]
    }
}