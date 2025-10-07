Setup Instructions:
pip install networkx matplotlib numpy

Place the following files in the same folder:
graph_analysis.py
graph.gml
edges.csv

Sample Command-Line Usage:

Partition graph, plot clustering, simulate edge failures:
python .\graph_analysis.py graph.gml --components 3 --plot C --simulate_failures 5 --output output.gml

Run temporal simulation and create an animated GIF:
python .\graph_analysis.py graph.gml --plot T --temporal_simulation edges.csv --temporal_gif evolution.gif

Verify homophily and structural balance:
python .\graph_analysis.py graph.gml --verify_homophily --verify_balanced_graph --output output.gml

Explanation of Approach:
-The program loads a .gml graph and computes key network metrics using NetworkX.
-Clustering coefficients measure how connected each node’s neighbors are.
-Neighborhood overlap compares shared neighbors between linked nodes.
-The Girvan–Newman algorithm partitions the graph into communities by progressively removing high-betweenness edges.
-Homophily is tested with a t-test on node similarity based on color-coded attributes.
-Structural balance checks if signed edges form consistent triads.
-Failure simulation removes random edges to see changes in path length, connectivity, and betweenness.
-Robustness repeats these simulations to find average structural stability.
-Temporal simulation loads edge changes from a CSV and animates the graph’s evolution over time.