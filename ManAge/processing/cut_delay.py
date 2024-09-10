from dataclasses import dataclass, field
from typing import List, Tuple
from joblib import Parallel, delayed

@dataclass
class CUT_Delay:
    origin          : str           = 'X-1Y-1'
    CUT_idx         : int           = -1
    TC_idx          : int           = -1
    seg_idx         : int           = -1
    path_idx        : int           = -1  # this is the index of the CUT in the segment
    rising_delay    : float         = 0
    falling_delay   : float         = 0
    both_delay      : float         = 0
    edges           : List[Tuple]   = field(default_factory=list)


    def __eq__(self, other):
        return type(self) == type(other) and self.origin == other.origin and self.CUT_idx == other.CUT_idx and self.TC_idx == other.TC_idx

    def __hash__(self):
        return hash((self.origin, self.CUT_idx, self.TC_idx))

@dataclass
class CUTs_List:
    CUTs    :   List[CUT_Delay]

    def add_cut(self, cut, TC_idx):
        edges = cut.main_path.get_edges()
        cut_delay = CUT_Delay(origin=cut.origin, CUT_idx=cut.index, TC_idx=TC_idx, edges=edges)
        self.CUTs.append(cut_delay)

    def filter_CUTs(self, **attributes):
        all_cuts = self.CUTs.copy()
        for k, v in attributes.items():
            cuts = set()
            for cut in all_cuts:
                if getattr(cut, k) == v:
                    cuts.add(cut)

            all_cuts = cuts.copy()

        return all_cuts

    def get_coord_cut_dict(self):
        coord_cut_dict = {}
        for cut in self.CUTs:
            if cut.origin not in coord_cut_dict:
                coord_cut_dict[cut.origin] = [cut]
            else:
                coord_cut_dict[cut.origin].append(cut)

        return coord_cut_dict

    def get_delay_dicts(self):
        # get coord_cut_dict
        coord_cut_dict = self.get_coord_cut_dict()

        results = Parallel(n_jobs=1)(
            delayed(self.get_average_delay)(coord, cuts) for coord, cuts in coord_cut_dict.items()
        )

        # Convert results into dictionaries
        rising_dict = {coord: rising_avg for coord, rising_avg, _, _ in results}
        falling_dict = {coord: falling_avg for coord, _, falling_avg, _ in results}
        both_dict = {coord: both_avg for coord, _, _, both_avg in results}

        return rising_dict, falling_dict, both_dict

    @staticmethod
    def get_average_delay(coord, cuts):
        edges = [edge for cut in cuts for edge in cut.edges]
        rising_avg = sum(cut.rising_delay for cut in cuts) / len(edges)
        falling_avg = sum(cut.falling_delay for cut in cuts) / len(edges)
        both_avg = sum(cut.both_delay for cut in cuts) / len(edges)

        return coord, rising_avg, falling_avg, both_avg