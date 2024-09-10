# Procedure to parse command-line arguments
proc parse_args {argv valid_flags valid_options cmd_exist} {
    set cmd ""
    set positional_args [list]
    set options [dict create]

    # Initialize all flags to 0 (absent)
    foreach flag [dict keys $valid_flags] {
        dict set options $flag 0
    }

    # Check if at least one argument is provided
    if {[llength $argv] == 0} {
        puts "Error: No command provided"
        return -code error
    }

    # Extract the subcommand (first argument)
    if {$cmd_exist} {
        set cmd [lindex $argv 0]
        set argv [lrange $argv 1 end]
    }

    set i 0
    while {$i < [llength $argv]} {
        set arg [lindex $argv $i]
        
        if {[dict exists $valid_flags $arg]} {
            # Handle flags (no value expected)
            dict set options $arg 1
        } elseif {[dict exists $valid_options $arg]} {
            # Handle options (value expected)
            if {$i + 1 < [llength $argv]} {
                set option_value [lindex $argv [expr {$i + 1}]]
                if {[string match -* $option_value]} {
                    puts "Error: Missing value for option '$arg'"
                    return -code error
                }
                dict set options $arg $option_value
                incr i
            } else {
                puts "Error: Missing value for option '$arg'"
                return -code error
            }
        } else {
            # Positional argument detected
            lappend positional_args $arg
        }
        incr i
    }

    # Return the parsed command, positional arguments, and options
    return [list $cmd $positional_args $options]
}

# Procedure to generate the bitstream
proc gen_bitstream {proj_dir proj_name vivado_sources_dir N_Segments N_Parallel N_Partial bitstream_file dcp_file} {
		set CUTs "$vivado_sources_dir/CUTs.vhd"
		set constraint "$vivado_sources_dir/physical_constraints.xdc"
		set bd_file "$proj_dir/$proj_name\.srcs/sources_1/bd/design_1/design_1.bd"

	# delete previous implementation
	catch {reset_run synth_1}
	catch {reset_run impl_1}
	delete_runs synth_1

	# replace CUTs
	replace_VHDL_src $CUTs
	set_property file_type {VHDL 2008} [get_files $CUTs]
	
	# replace physical_constraints
	replace_constraints $constraint
	set_property used_in_synthesis false [get_files "$constraint"]

	# update compile order
	update_compile_order -fileset sources_1
	update_module_reference design_1_top_0_0

	# replace new N_Segments & N_Partial
	open_bd_design "$bd_file"
	set_property -dict [list CONFIG.g_n_parallel $N_Parallel CONFIG.g_segments $N_Segments CONFIG.g_n_partial $N_Partial] [get_bd_cells top_0]

	# validate board design
	save_bd_design
	validate_bd_design

	# implement design
	catch {launch_runs impl_1 -jobs 12}
	catch {wait_on_run impl_1}

	# store bitstream & DCP
	open_run impl_1
	set_property BITSTREAM.GENERAL.COMPRESS TRUE [current_design]
	write_bitstream -force $bitstream_file
	write_checkpoint -force $dcp_file
}

proc replace_VHDL_src {current_src} {
	set src_name [lindex [split $current_src /] end]
	set prev_src [get_files $src_name]
	if {[llength $prev_src] > 0} {
		remove_files  -fileset sources_1 "$prev_src"
	}
	add_files -fileset sources_1 -norecurse $current_src
}

proc replace_constraints {current_constraint} {
	set const_name [lindex [split $current_constraint /] end]
	set prev_constraint [get_files $const_name]
	if {[llength $prev_constraint] > 0} {
		remove_files  -fileset constrs_1 "$prev_constraint"
	}
	add_files -fileset constrs_1 -norecurse "$current_constraint"
}

proc get_segmentation {stats} {
	set file [open "$stats" r]
	set lines [read "$file"]
	regexp {(\d+).* (\d+)} $lines match N_Segments N_Partial
	
	return [list $N_Segments $N_Partial]
}

# Set options
set valid_flags [dict create "-overwrite" 1]
set valid_options [dict create]
set cmd_exist 0


# Parse options
set parsed_data [parse_args $argv $valid_flags $valid_options $cmd_exist]
set cmd [lindex $parsed_data 0]
set positional_args [lindex $parsed_data 1]
set options [lindex $parsed_data 2]

# Assign positional_args
set proj_file [lindex $positional_args 0]
set vivado_sources_dir [lindex $positional_args 1]

set N_Segments [lindex $positional_args 2]
set N_Parallel [lindex $positional_args 3]
set N_Partial [lindex $positional_args 4]

set bitstream_file [lindex $positional_args 5]
set dcp_file [lindex $positional_args 6]
set log_file [lindex $positional_args 7]

####
# puts $proj_file
# puts $vivado_sources_dir
# puts $N_Segments
# puts $N_Parallel
# puts $N_Partial
# puts $bitstream_file
# puts $dcp_file
# puts $log_file
# puts $options
# exit
####

# Extract project directory and file name
set proj_name [file rootname [file tail $proj_file]]
set proj_dir [file dirname $proj_file]

if {[catch {current_project $proj_name} result]} {
	# open project
	if {[catch {open_project "$proj_file"} result]} {
		puts "Specified Xilinx project file is invalid!\n$proj_dir"
	}
} 

# change severity of critical warnings to error
set_msg_config -severity {CRITICAL WARNING} -new_severity ERROR

if {[file exists $log_file] && ![dict get $options "-overwrite"]} {
			exit
}

# Implement design
catch {gen_bitstream $proj_dir $proj_name $vivado_sources_dir $N_Segments $N_Parallel $N_Partial $bitstream_file $dcp_file}

# Copy the log file
set default_log_file "$proj_dir/$proj_name\.runs/impl_1/runme.log"
file copy -force $default_log_file $log_file
