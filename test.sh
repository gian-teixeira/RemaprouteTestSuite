declare -A folders=(\
	#["ufmg"]=/home/giancarlo/paths/final/parsed_ufmg01 \
	#["vtrjohannesburg"]=/home/giancarlo/paths/final/parsed_vtrjohannesburg \
	#["vtrseoul"]=/home/giancarlo/paths/final/parsed_vtrseoul \
	["vtrsilicon"]=/home/giancarlo/paths/final/parsed_vtrsilicon \
	#["vtrmumbai"]=/home/giancarlo/paths/final/parsed_vtrmumbai \
)

for key in ${!folders[@]}; do
	bash exec.sh ${folders[$key]}
	rm -rf test/$key
	mkdir test/$key
	cp -r ~/simulator/out/* test/$key
done
