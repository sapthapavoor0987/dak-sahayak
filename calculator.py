import math

# Official Speed Post Distance & Weight Tariff Matrix
TARIFF_MATRIX = {
    "local": {
        "label": "Local (Intra-city)",
        "up_to_50g": 15,
        "up_to_200g": 25,
        "up_to_500g": 30,
        "addl_500g": 10
    },
    "up_to_200": {
        "label": "Up to 200 km",
        "up_to_50g": 35,
        "up_to_200g": 35,
        "up_to_500g": 50,
        "addl_500g": 15
    },
    "201_to_1000": {
        "label": "201 to 1000 km",
        "up_to_50g": 35,
        "up_to_200g": 40,
        "up_to_500g": 60,
        "addl_500g": 30
    },
    "1001_to_2000": {
        "label": "1001 to 2000 km",
        "up_to_50g": 35,
        "up_to_200g": 60,
        "up_to_500g": 80,
        "addl_500g": 40
    },
    "above_2000": {
        "label": "Above 2000 km",
        "up_to_50g": 35,
        "up_to_200g": 70,
        "up_to_500g": 90,
        "addl_500g": 50
    }
}

def resolve_distance_category(distance_input):
    """Normalizes numeric km or category string to valid tariff matrix key."""
    if isinstance(distance_input, (int, float)):
        km = float(distance_input)
        if km <= 0:
            return "local"
        elif km <= 200:
            return "up_to_200"
        elif km <= 1000:
            return "201_to_1000"
        elif km <= 2000:
            return "1001_to_2000"
        else:
            return "above_2000"
    
    key = str(distance_input).lower().strip().replace(" ", "_")
    if key in TARIFF_MATRIX:
        return key
    if "local" in key:
        return "local"
    if "200" in key and "1000" not in key:
        return "up_to_200"
    if "1000" in key and "2000" not in key:
        return "201_to_1000"
    if "2000" in key and "above" in key or "above_2000" in key:
        return "above_2000"
    if "2000" in key:
        return "1001_to_2000"
    
    return "up_to_200"

def calculate_speed_post(weight_g, distance_input):
    """
    Calculates Domestic Speed Post charges based on weight (grams) and distance slab.
    Returns base tariff, 18% GST, and total payable amount.
    """
    try:
        weight = float(weight_g)
    except (ValueError, TypeError):
        weight = 50.0

    if weight <= 0:
        weight = 1.0

    dist_key = resolve_distance_category(distance_input)
    rates = TARIFF_MATRIX[dist_key]
    
    base_tariff = 0
    weight_slab = ""

    if weight <= 50:
        base_tariff = rates["up_to_50g"]
        weight_slab = "Up to 50 g"
    elif weight <= 200:
        base_tariff = rates["up_to_200g"]
        weight_slab = "51 g to 200 g"
    elif weight <= 500:
        base_tariff = rates["up_to_500g"]
        weight_slab = "201 g to 500 g"
    else:
        base_tariff = rates["up_to_500g"]
        extra_weight = weight - 500
        extra_slabs = math.ceil(extra_weight / 500.0)
        additional_cost = extra_slabs * rates["addl_500g"]
        base_tariff += additional_cost
        weight_slab = f"500 g + {extra_slabs} x 500g additional"

    gst_amount = round(base_tariff * 0.18, 2)
    total_payable = round(base_tariff + gst_amount, 2)

    return {
        "service": "Speed Post",
        "weight_g": weight,
        "distance_key": dist_key,
        "distance_label": rates["label"],
        "weight_slab": weight_slab,
        "base_tariff": base_tariff,
        "gst_rate": "18%",
        "gst_amount": gst_amount,
        "total_payable": total_payable
    }

def calculate_ordinary_letter(weight_g):
    """First 20g = Rs. 5. Every additional 20g = Rs. 5 (Max 2 kg)."""
    try:
        weight = float(weight_g)
    except (ValueError, TypeError):
        weight = 20.0
    weight = max(1.0, min(2000.0, weight))

    slabs = math.ceil(weight / 20.0)
    total_cost = slabs * 5.0
    return {
        "service": "Ordinary Letter",
        "weight_g": weight,
        "slabs": slabs,
        "base_tariff": total_cost,
        "total_payable": total_cost
    }

def calculate_postcard(card_type="single"):
    """Single = Rs. 0.50, Reply = Rs. 1.00, Printed = Rs. 6.00, Competition = Rs. 10.00."""
    card_type_clean = str(card_type).lower().strip()
    rates = {
        "single": 0.50,
        "reply": 1.00,
        "printed": 6.00,
        "competition": 10.00
    }
    price = rates.get(card_type_clean, 0.50)
    return {
        "service": "Postcard",
        "type": card_type_clean,
        "total_payable": price
    }

def calculate_inland_letter():
    """Inland Letter Card = Rs. 2.50 flat."""
    return {
        "service": "Inland Letter Card",
        "total_payable": 2.50
    }

def calculate_ordinary_parcel(weight_g):
    """First 500g = Rs. 19. Every additional 500g = Rs. 16."""
    try:
        weight = float(weight_g)
    except (ValueError, TypeError):
        weight = 500.0
    weight = max(1.0, weight)

    if weight <= 500:
        cost = 19.0
    else:
        extra_weight = weight - 500
        extra_slabs = math.ceil(extra_weight / 500.0)
        cost = 19.0 + (extra_slabs * 16.0)

    return {
        "service": "Ordinary Parcel",
        "weight_g": weight,
        "base_tariff": cost,
        "total_payable": cost
    }

def calculate_registered_post(postage_base=5.0, ad_required=False):
    """Registration Fee = Rs. 17. Optional AD card = Rs. 3 extra."""
    reg_fee = 17.0
    ad_fee = 3.0 if ad_required else 0.0
    total = postage_base + reg_fee + ad_fee
    return {
        "service": "Registered Post",
        "postage": postage_base,
        "registration_fee": reg_fee,
        "ad_card_fee": ad_fee,
        "total_payable": total
    }

def calculate_insurance(value_amount):
    """Up to Rs. 200 = Rs. 10. Every additional Rs. 100 = Rs. 6."""
    try:
        val = float(value_amount)
    except (ValueError, TypeError):
        val = 200.0
    val = max(1.0, val)

    if val <= 200:
        fee = 10.0
    else:
        extra_val = val - 200
        extra_slabs = math.ceil(extra_val / 100.0)
        fee = 10.0 + (extra_slabs * 6.0)

    return {
        "service": "Insurance Fee",
        "insured_value": val,
        "insurance_fee": fee
    }

if __name__ == "__main__":
    print("Speed Post 350g 1500km:", calculate_speed_post(350, 1500))
    print("Ordinary Letter 45g:", calculate_ordinary_letter(45))
    print("Ordinary Parcel 1200g:", calculate_ordinary_parcel(1200))
    print("Registered Post + AD:", calculate_registered_post(5.0, ad_required=True))
    print("Insurance Rs. 500:", calculate_insurance(500))
