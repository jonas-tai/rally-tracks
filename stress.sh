while getopts c:m:t:s:l: flag; do
    case "${flag}" in
    c) CPU=${OPTARG} ;;
    m) MEMORY=${OPTARG} ;;
    t) TIME=${OPTARG} ;;
    s) SLEEP=${OPTARG} ;;
    l) LIMIT=${OPTARG} ;;
    esac
done

STEP_SIZE=$((TIME + SLEEP))

# for ((i = 0; i < ${LIMIT}; i += STEP_SIZE)); do
#     stress -c ${CPU} -t ${TIME} -m ${MEMORY} -i ${MEMORY} -d ${MEMORY}
#     sleep ${SLEEP}s
# done

for ((i = 0; i < ${LIMIT}; i += STEP_SIZE)); do
    stress-ng --matrix ${CPU} -t ${TIME}
    sleep ${SLEEP}s
done