BASE_URL = "https://bhoonidhi.nrsc.gov.in"
session_info = {"jwt": None,"userId": None, "user_email": None, "username": None, 'sid': None, 'scenes': []}

satellite_sensor_map = {
    'RS1': {
        "LISS3": "ResourceSat-1_LISS3",
        "LISS4": "ResourceSat-1_LISS4(MONO)",
        "AWIFS": "ResourceSat-1_AWIFS_1x1deg-tiles" # Low Resolution Imagery (25 - 100m)
    },
    'RS2': {
        "LISS3": ["ResourceSat-2_LISS3", "ResourceSat-2_LISS3_BOA", "ResourceSat-2_LISS3_L2"],
        "LISS4": ["ResourceSat-2_LISS4(MX23)", "ResourceSat-2_LISS4(MX70)", "ResourceSat-2_LISS4(MX70)_L2"],
        "AWIFS": [ # Low Resolution Imagery (25 - 100m)
            "ResourceSat-2_AWIFS_BOA",
            "ResourceSat-2_AWIFS_L2",
            "ResourceSat-2_AWIFS_NDVI-10x10deg-tiles_15day_100m",
            "ResourceSat-2_AWIFS_1x1deg-tiles",
            "ResourceSat-2_AWIFS_10x10deg-tiles_15day_100m",
            "ResourceSat-2_AWIFS_10x10deg-tiles_5day_100m"
        ]
    },
    'RS2A': {
        "LISS3": ["ResourceSat-2A_LISS3", "ResourceSat-2A_LISS3_BOA", "ResourceSat-2A_LISS3_L2"],
        "LISS4": ["ResourceSat-2A_LISS4(MX23)", "ResourceSat-2A_LISS4(MX70)", "ResourceSat-2A_LISS4(MX70)_L2"],
        "AWIFS": ["ResourceSat-2A_AWIFS_BOA", "ResourceSat-2A_AWIFS_L2"] # Low Resolution Imagery (25 - 100m)
    },
    'S2A': {
        "MSI": ["Sentinel-2A_MSI_Level-1C", "Sentinel-2A_MSI_Level-2A"]
    },
    'S2B': {
        "MSI": ["Sentinel-2B_MSI_Level-1C", "Sentinel-2B_MSI_Level-2A"]
    },
    'IRS1C': {
        "PAN": ["IRS-1C_PAN"], 
        "WIFS": ["IRS-1C_WIFS"] # Low Resolution Imagery (25 - 100m)
    },
    'IRS1D': {
        "PAN": ["IRS-1D_PAN"],
        "LISS3": ["IRS-1D_LISS3"],
        "WIFS": ["IRS-1D_WIFS"] # Low Resolution Imagery (25 - 100m)
    },
    'S1A': {
        "SAR": ["Sentinel-1A_SAR(IW)_GRD", "Sentinel-1A_SAR(IW)_SLC"]
    },
    'S1B': {
        "SAR": ["Sentinel-1B_SAR(IW)_GRD"],
    },
    ###### Low Resolution Imagery (25 - 100m) ######
    'CartoSat-1': {
        "PAN": ["CartoSat-1_PAN_CartoDEM-30m"]
    },
    'EOS-04': {
        "SAR": [
            "EOS-04_SAR(CRS)_L2B",
            "EOS-04_SAR(CRS)_L2A",
            "EOS-04_SAR(MRS)_L2B",
            "EOS-04_SAR(MRS)_L2A",
            "EOS-04_SAR(MRS)_SM"
        ]
    },
    'IRS-1A': {
        "LISS1": ["IRS-1A_LISS1"],
        "LISS2": ["IRS-1A_LISS2"]
    },
    'IRS-1B': {
        "LISS1": ["IRS-1B_LISS1"],
        "LISS2": ["IRS-1B_LISS2"]
    },
    'LandSat-8': {
        "OLI+TIRS": ["LandSat-8_OLI%2BTIRS_L1"] # LandSat-8_OLI+TIRS_L1
    },    
    'LandSat-9': {
        "OLI+TIRS": ["LandSat-9_OLI%2BTIRS_L1"] # LandSat-9_OLI+TIRS_L1
    },
}