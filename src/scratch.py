# ---------------------------------------------- #
def transform_interval(intersect):
    if(intersect <= 0.0):
        return "0"
    elif(intersect <= 0.2 and intersect > 0.0):
        return "1-20"
    elif(intersect <= 0.4 and intersect > 0.2):
        return "20-40"
    elif(intersect <= 0.6 and intersect > 0.4):
        return "40-60"
    elif(intersect <= 0.8 and intersect > 0.6):
        return "60-80"
    elif(intersect <= 1.0 and intersect > 0.8):
        return "80-100"
    #elif(intersect >= 1.0):
    #    return "100"

    return "none"

# --------------------------------------------- #
def gen_cdf_list(elements):

    cdf = list()

    total = len(elements)
    keys = list(set(elements))
    keys.sort()
    acc = 0

    for key in keys:
        acc += elements.count(key)
        cdf.append((key, acc/float(total)))

    return cdf

# --------------------------------------------- #
def gen_cdf_dict(elements):

    cdf = list()

    keys = list(elements.keys())
    keys.sort()

    # Get total
    total = 0
    for key in keys:
        total += elements[key]

    acc = 0
    for key in keys:
        acc += elements[key]
        cdf.append((key, acc/float(total)))

    return cdf