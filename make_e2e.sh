set -e

TOTAL_CLIENTS_HIGH_LOAD=7
TOTAL_CLIENTS_MED_HIGH_LOAD=7
TOTAL_CLIENTS_MED_LOAD=6
OUT_FOLDER="elastic/logs/workflows/custom/end_to_end_alternating"

MICROBENCHMARK_TIME=900

HIGH_LOAD="--draw_size True --zipf 1 --clients ${TOTAL_CLIENTS_HIGH_LOAD} --target_clients ${TOTAL_CLIENTS_HIGH_LOAD} --pareto 0.63 --size_max 5 --request_range 20 --load_period 10 --min_load 1 --size_multiplier 1 --draw_size_zero"
HIGH_EVICT="--draw_size True --zipf 1 --clients ${TOTAL_CLIENTS_MED_LOAD} --target_clients ${TOTAL_CLIENTS_HIGH_LOAD} --pareto 0.4 --size_max 25 --request_range 30  --load_period 10 --min_load 1 --size_multiplier 1 --draw_size_zero"
HIGH_CACHE="--draw_size True --zipf 2 --clients ${TOTAL_CLIENTS_MED_LOAD} --target_clients ${TOTAL_CLIENTS_HIGH_LOAD} --pareto 0.6 --size_max 1 --request_range 30  --load_period 10 --min_load 1 --size_multiplier 1 --draw_size_zero"
STRESSED_NODES="--draw_size True --zipf 1 --clients ${TOTAL_CLIENTS_MED_LOAD} --target_clients ${TOTAL_CLIENTS_HIGH_LOAD} --pareto 0.63 --size_max 5 --request_range 20 --load_period 10 --min_load 1 --size_multiplier 1 --draw_size_zero"

SEED="1"
OUT_PATH="elastic/logs/workflows/custom/microbenchmarks"
python make_workload.py ${HIGH_LOAD} --out_folder ${OUT_PATH}/high_load --mode 'n' --max_workload_time ${MICROBENCHMARK_TIME} --seed ${SEED}
python make_workload.py ${HIGH_CACHE} --out_folder ${OUT_PATH}/high_cache --mode 'n' --max_workload_time ${MICROBENCHMARK_TIME} --seed ${SEED}
python make_workload.py ${HIGH_EVICT} --out_folder ${OUT_PATH}/high_evict --mode 'n' --max_workload_time ${MICROBENCHMARK_TIME} --seed ${SEED}
python make_workload.py ${STRESSED_NODES} --out_folder ${OUT_PATH}/stressed_nodes --mode 'n' --max_workload_time ${MICROBENCHMARK_TIME} --seed ${SEED}

OUT_PATH="${OUT_FOLDER}/1"
SEED="1"

python make_workload.py ${HIGH_LOAD} --out_folder ${OUT_PATH} --mode 'n' --max_workload_time 300 --seed ${SEED}
python make_workload.py ${HIGH_LOAD} --out_folder ${OUT_PATH} --mode '' --max_workload_time 1301 --seed ${SEED}
python make_workload.py ${HIGH_EVICT} --out_folder ${OUT_PATH} --mode '' --max_workload_time 542 --seed ${SEED}
python make_workload.py ${HIGH_CACHE} --out_folder ${OUT_PATH} --mode '' --max_workload_time 1399 --seed ${SEED}
python make_workload.py ${HIGH_EVICT} --out_folder ${OUT_PATH} --mode '' --max_workload_time 1002 --seed ${SEED}

OUT_PATH="${OUT_FOLDER}/2"
SEED="2"
python make_workload.py ${HIGH_LOAD} --out_folder ${OUT_PATH} --mode 'n' --max_workload_time 1232 --seed ${SEED}
python make_workload.py ${HIGH_CACHE} --out_folder ${OUT_PATH} --mode '' --max_workload_time 1732 --seed ${SEED}
python make_workload.py ${HIGH_EVICT} --out_folder ${OUT_PATH} --mode '' --max_workload_time 1590 --seed ${SEED}

OUT_PATH="${OUT_FOLDER}/3"
SEED="3"
python make_workload.py ${HIGH_LOAD} --out_folder ${OUT_PATH} --mode 'n' --max_workload_time 1710 --seed ${SEED}
python make_workload.py ${HIGH_CACHE} --out_folder ${OUT_PATH} --mode '' --max_workload_time 1120 --seed ${SEED}
python make_workload.py ${HIGH_EVICT} --out_folder ${OUT_PATH} --mode 'e' --max_workload_time 1735 --seed ${SEED}
