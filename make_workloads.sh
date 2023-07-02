python elastic/logs/custom_workflows.py --multiplier 30 --outfolder custom/30
python elastic/logs/custom_workflows.py --multiplier 90 --outfolder custom/90
python elastic/logs/custom_workflows.py --fixed_duration 90 --size_min 500 --outfolder custom/90/norequestcache
python elastic/logs/custom_workflows.py --fixed_duration 30 --size_min 250 --outfolder custom/30/norequestcache
python elastic/logs/custom_workflows.py --fixed_duration 15 --size_min 10 --outfolder custom/15/norequestcache