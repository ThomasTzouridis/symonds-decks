import re
def cat(ind):
    i=(ind or '').lower()
    if not i: return 'Other'
    if i in ('staffing and recruiting','executive search services'): return 'Staffing'
    if i in ('real estate','interior design'): return 'Real estate'
    if i in ('financial services','insurance','investment management','banking','venture capital and private equity principals','loan brokers','investment, funds and trusts'): return 'Financial services and insurance'
    if 'manufacturing' in i or i in ('automotive','wholesale building materials','building materials','general wholesale','shipbuilding','oil, gas, and mining','renewable energy','electric power generation','printing services','aviation & aerospace','consumer goods'): return 'Manufacturing'
    if i in ('construction','facilities services','environmental services','landscaping services','specialty trade contractors','janitorial services','civil engineering'): return 'Construction'
    if i in ('hospitals and health care','mental health care','wellness and fitness services','medical practices','dentists','veterinary services','alternative medicine','physical, occupational and speech therapists','home health care services','medical and diagnostic laboratories','biotechnology research'): return 'Healthcare'
    if i in ('advertising services','marketing services','media production and publishing','public relations and communications services','events services','design services','photography','animation and post-production','artists and writers','market research'): return 'Agencies'
    if i in ('business consulting and services','it services and it consulting','software development','technology, information and internet','accounting','law practice','legal services','architecture and planning','engineering services','professional training and coaching','human resources services','human resources','mechanical or industrial engineering','strategic management services','research services','translation and localization','computer and network security','telecommunications','e-learning providers','executive offices','administrative and support services','wireless services','international trade and development','security and investigations'): return 'Professional services'
    return 'Other'
