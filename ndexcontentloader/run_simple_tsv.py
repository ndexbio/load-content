__author__ = 'aarongary'
import ndextsv.delim2cx as d2c
import ndex.client as nc
import os

if False:
    import_plan = d2c.TSVLoadingPlan(os.path.join('import_plans', 'Justin1.json'))

    tsv_converter = d2c.TSV2CXConverter(import_plan)

    my_ndex = nc.Ndex("http://dev2.ndexbio.org", 'scratch','scratch')

    ng = tsv_converter.convert_tsv_to_cx(os.path.join('import', 'DIP_Symbol.txt'), name='my network name', description='my network description')

    mystr=''
#else:
    import requests

    url = 'http://ec2-52-34-7-132.us-west-2.compute.amazonaws.com:3000/upload?save_plan=false'
    #url = 'http://localhost:8183/upload?save_plan=false'

    files = {
        'plan': open('import_plans/Minkyu.json', 'rb'),
        'upload': open('import/MDA231_All_AP-MS_20170804_corrected.txt', 'rb')
    }

    data = {
        'template': '651f91a5-7d2c-11e7-9743-0660b7976219',
        'ndexServer': 'dev2.ndexbio.org',
        'user': 'aarongary',
        'pw': 'ccbbucsd',
        'name': 'my network',
        'description': 'this is my description'
    }

    r = requests.post(url, data=data, files=files)

    print r.content

#else:
    #my_url = 'http://dev2.ndexbio.org/v2/network/37ee1bb2-973d-11e7-9743-0660b7976219'
    #url_parts = my_url.split('/')
    #print url_parts[-1]
else:
    property_dict = {'a': 'a1'}
    for name, value in property_dict.items():
        print(name)
        print(value)
