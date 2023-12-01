set -e

TOTAL_CLIENTS_HIGH_LOAD=7
TOTAL_CLIENTS_MED_HIGH_LOAD=7
TOTAL_CLIENTS_MED_LOAD=6
OUT_FOLDER="elastic/logs/workflows/custom/microbenchmarks_early"

MICROBENCHMARK_TIME=900

HIGH_LOAD="--draw_size True --zipf 1 --clients ${TOTAL_CLIENTS_HIGH_LOAD} --target_clients ${TOTAL_CLIENTS_HIGH_LOAD} --pareto 0.63 --size_max 5 --request_range 20 --load_period 10 --min_load 1 --size_multiplier 1 --draw_size_zero"
HIGH_CACHE_SKEWED="--draw_size True --zipf 2 --clients ${TOTAL_CLIENTS_MED_LOAD} --target_clients ${TOTAL_CLIENTS_HIGH_LOAD} --pareto 0.6 --size_max 1 --request_range 30  --load_period 10 --min_load 1 --size_multiplier 1 --draw_size_zero --num_workflow_types 2"
HIGH_CACHE_UNIFORM="--draw_size True --zipf 0 --clients ${TOTAL_CLIENTS_MED_LOAD} --target_clients ${TOTAL_CLIENTS_HIGH_LOAD} --pareto 0.6 --size_max 1 --request_range 30  --load_period 10 --min_load 1 --size_multiplier 1 --draw_size_zero --num_workflow_types 2"
STRESSED_NODES="--draw_size True --zipf 1 --clients ${TOTAL_CLIENTS_MED_LOAD} --target_clients ${TOTAL_CLIENTS_HIGH_LOAD} --pareto 0.63 --size_max 5 --request_range 20 --load_period 10 --min_load 1 --size_multiplier 1 --draw_size_zero"

SEED="1"

python make_workload.py ${HIGH_LOAD} --out_folder ${OUT_PATH}/high_load --mode 'n' --max_workload_time ${MICROBENCHMARK_TIME} --seed ${SEED}
python make_workload.py ${HIGH_CACHE_SKEWED} --out_folder ${OUT_PATH}/high_cache_skewed --mode 'n' --max_workload_time ${MICROBENCHMARK_TIME} --seed ${SEED}
python make_workload.py ${HIGH_CACHE_UNIFORM} --out_folder ${OUT_PATH}/high_evict_uniform --mode 'n' --max_workload_time ${MICROBENCHMARK_TIME} --seed ${SEED}
python make_workload.py ${STRESSED_NODES} --out_folder ${OUT_PATH}/stressed_nodes --mode 'n' --max_workload_time ${MICROBENCHMARK_TIME} --seed ${SEED}
