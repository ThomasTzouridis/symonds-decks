"""Industry (HeyReach list field) -> deck category. Only the four verticals Dave Symonds targets (Thomas 2026-10-16)
have a deck version; everything else is "Other" and never gets a deck or message 1."""
def cat(ind):
    i = (ind or '').lower().strip()
    if not i: return 'Other'
    if i in ('construction', 'building construction', 'residential building construction', 'nonresidential building construction',
             'specialty trade contractors', 'civil engineering', 'architecture and planning', 'design build'): return 'Construction'
    if i in ('landscaping services', 'interior design', 'facilities services', 'consumer services', 'home improvement',
             'home services', 'furniture and home furnishings manufacturing', 'furniture', 'swimming pool construction'): return 'High end home services'
    if i in ('law practice', 'legal services', 'alternative dispute resolution'): return 'Law firms'
    if i in ('financial services', 'insurance', 'investment management', 'banking', 'venture capital and private equity principals',
             'loan brokers', 'investment, funds and trusts', 'investment banking', 'capital markets', 'accounting',
             'insurance agencies and brokerages', 'insurance carriers'): return 'Financial services'
    return 'Other'
