# bitstream file
set bit_file [lindex $argv 0]

# open hardware manager
open_hw_manager
connect_hw_server -url localhost:3121
current_hw_target [get_hw_targets *]
open_hw_target

# Program and Refresh the device
current_hw_device [lindex [get_hw_devices] 0]
refresh_hw_device -update_hw_probes false [lindex [get_hw_devices] 0]
#set_property PROBES.FILE {C:/Users/t26607bb/Desktop/Practice/CPS_ZCU104/CPS_Parallel_ZCU104/vivado_proj/CPS_Parallel_ZCU7.runs/impl_1/design_1_wrapper.ltx} [lindex [get_hw_devices] 0]
#set_property FULL_PROBES.FILE {C:/Users/t26607bb/Desktop/Practice/CPS_ZCU104/CPS_Parallel_ZCU104/vivado_proj/CPS_Parallel_ZCU7.runs/impl_1/design_1_wrapper.ltx} [lindex [get_hw_devices] 0]
set_property PROGRAM.FILE $bit_file [lindex [get_hw_devices] 0]
set_param xicom.use_bitstream_version_check false
program_hw_devices [lindex [get_hw_devices] 0]
refresh_hw_device [lindex [get_hw_devices] 0]