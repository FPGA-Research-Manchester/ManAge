from constraint.hdl import VHDL

def get_instantiation(CUT_idx, i_Clk_Launch, i_Clk_Sample, i_CE, i_CLR, o_Error, g_Buffer):
    codes = []
    codes.append(f'CUT_{CUT_idx}:\tentity work.CUT_Buff\n')
    codes.append(f'\tgeneric map(g_Buffer => "{g_Buffer}")\n')
    codes.append(f'\tport map({i_Clk_Launch}, {i_Clk_Sample}, {i_CE}, {i_CLR}, {o_Error});\n')
    return codes


def get_VHDL_file():
    VHDL_file = VHDL('CUTs', 'behavioral')
    VHDL_file.add_package('ieee', 'std_logic_1164')
    VHDL_file.add_package('work', 'my_package')
    VHDL_file.add_generic('g_N_Segments', 'integer')
    VHDL_file.add_generic('g_N_Parallel', 'integer')
    VHDL_file.add_port('i_Clk_Launch', 'in', 'std_logic')
    VHDL_file.add_port('i_Clk_Sample', 'in', 'std_logic')
    VHDL_file.add_port('i_CE', 'in', 'std_logic')
    VHDL_file.add_port('i_CLR', 'in', 'std_logic')
    VHDL_file.add_port('o_Error', 'out', 'my_array')
    VHDL_file.add_signal('w_Error', 'my_array(0 to g_N_Segments - 1)(g_N_Parallel - 1 downto 0)',
                         "(others => (others => '1'))")
    VHDL_file.add_assignment('o_Error', 'w_Error')

    return VHDL_file
