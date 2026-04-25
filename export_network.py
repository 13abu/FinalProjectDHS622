import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from final_project.utilities.logic import export_network_to_gexf

export_network_to_gexf(
    seed_list="iran_israel_war",
    start_date="2026-02-01",
    end_date="2026-04-14",
    output_path="network.gexf"
)