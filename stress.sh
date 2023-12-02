while getopts c:m:t:s:l:o: flag; do
    case "${flag}" in
    c) CPU=${OPTARG} ;;
    m) MEMORY=${OPTARG} ;;
    t) TIME=${OPTARG} ;;
    s) SLEEP=${OPTARG} ;;
    l) LIMIT=${OPTARG} ;;
    o) OFFSET=${OPTARG} ;;
    esac
done

STEP_SIZE=$((TIME + SLEEP))

sleep ${OFFSET}s

for ((i = 0; i < ${LIMIT}; i += STEP_SIZE)); do
    stress-ng --matrix ${CPU} -t ${TIME} --copy-file ${CPU}
    sleep ${SLEEP}s
done