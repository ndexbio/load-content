### Standard command line arguments are as follows:

```username password -s public.ndexbio.org```

### Custom arguments are as follows:

```username password -s dev.ndexbio.org --file "Single Gene Cistromics NNMT_v2.txt" --plan spp_single_cx_option1-plan.json -t 6ed4180d-e445-11e8-8872-525400c25d22```

### Argument descriptions
-s (NDEx server to load network(s) to)
-t (UUID of a graphic template)

--file (Edge list file name.  Default is to run imports from load_list.json)
--plan (Import plan file name)
--update (Update existing network.  Keep metadata.  Default is True)
