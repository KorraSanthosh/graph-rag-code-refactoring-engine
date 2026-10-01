def apply_tax(amount):
    return amount * 1.08


def get_discount(total, is_member):
    if is_member == True:
        if total > 100:
            d = 0.15
        else:
            if total > 50:
                d = 0.10
            else:
                d = 0.05
    else:
        if total > 100:
            d = 0.05
        else:
            d = 0
    return d


def calculate_order_total(prices, is_member):
    total = 0
    for p in prices:
        total = total + p
    discount = get_discount(total, is_member)
    discounted = total - total * discount
    final = apply_tax(discounted)
    result = round(final, 2)
    return result
