set -e

TOTAL_CLIENTS_HIGH_LOAD=8
TOTAL_CLIENTS_MED_LOAD=6
OUT_FOLDER="elastic/logs/workflows/custom/end_to_end_alternating"

HIGH_LOAD="--draw_size False --zipf 1 --clients ${TOTAL_CLIENTS_HIGH_LOAD} --target_clients ${TOTAL_CLIENTS_HIGH_LOAD} --pareto 0.63 --size_max 25 --request_range 20 --load_period 10 --min_load 1 --size_multiplier 1"
HIGH_EVICT="--draw_size True --zipf 1 --clients ${TOTAL_CLIENTS_MED_LOAD} --target_clients ${TOTAL_CLIENTS_HIGH_LOAD} --num_workflow_types 6 --pareto 0.4 --size_max 40 --request_range 30  --load_period 10 --min_load 1 --size_multiplier 1"
HIGH_CACHE="--draw_size True --zipf 3 --clients ${TOTAL_CLIENTS_MED_LOAD} --target_clients ${TOTAL_CLIENTS_HIGH_LOAD} --num_workflow_types 2 --pareto 0.6 --size_max 25 --request_range 30  --load_period 10 --min_load 1 --size_multiplier 1"

OUT_PATH="${OUT_FOLDER}/1"

python make_workload.py ${HIGH_LOAD} --out_folder ${OUT_PATH} --mode 'n' --max_workload_time 300
python make_workload.py ${HIGH_LOAD} --out_folder ${OUT_PATH} --mode '' --max_workload_time 1301
python make_workload.py ${HIGH_EVICT} --out_folder ${OUT_PATH} --mode '' --max_workload_time 542
python make_workload.py ${HIGH_CACHE} --out_folder ${OUT_PATH} --mode '' --max_workload_time 1399
python make_workload.py ${HIGH_EVICT} --out_folder ${OUT_PATH} --mode '' --max_workload_time 902

OUT_PATH="${OUT_FOLDER}/2"

python make_workload.py ${HIGH_LOAD} --out_folder ${OUT_PATH} --mode '' --max_workload_time 1232
python make_workload.py ${HIGH_CACHE} --out_folder ${OUT_PATH} --mode '' --max_workload_time 1732
python make_workload.py ${HIGH_EVICT} --out_folder ${OUT_PATH} --mode '' --max_workload_time 1490

OUT_PATH="${OUT_FOLDER}/3"

python make_workload.py ${HIGH_LOAD} --out_folder ${OUT_PATH} --mode '' --max_workload_time 1710
python make_workload.py ${HIGH_CACHE} --out_folder ${OUT_PATH} --mode '' --max_workload_time 1120
python make_workload.py ${HIGH_EVICT} --out_folder ${OUT_PATH} --mode '' --max_workload_time 1635

OUT_PATH="${OUT_FOLDER}/4"
python make_workload.py ${HIGH_CACHE} --out_folder ${OUT_PATH} --mode '' --max_workload_time 1735
python make_workload.py ${HIGH_LOAD} --out_folder ${OUT_PATH} --mode 'e' --max_workload_time 2044


#python make_workload.py --size_max 50 --request_range 20 --clients 12 --out_folder elastic/logs/workflows/custom/end_to_end --load_period 10 --min_load 1 --size_multiplier 1 --draw_size False --zipf 1 --mode 'n' --target_clients 12 --max_workload_time 1200 --pareto 0.63
#python make_workload.py --size_max 50 --request_range 30 --clients 10 --out_folder elastic/logs/workflows/custom/end_to_end --load_period 10 --min_load 1 --size_multiplier 1 --draw_size True --zipf 1 --mode '' --target_clients 12 --max_workload_time 1200 --num_workflow_types 6 --pareto 0.4
#python make_workload.py --size_max 50 --request_range 30 --clients 10 --out_folder elastic/logs/workflows/custom/end_to_end --load_period 10 --min_load 1 --size_multiplier 1 --draw_size True --zipf 3 --mode 'e' --target_clients 12 --max_workload_time 1500 --num_workflow_types 2 --pareto 0.6
