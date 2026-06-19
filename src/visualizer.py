import os
import networkx as nx
import matplotlib.pyplot as plt

def generate_risk_graph(engine, output_path):
    """
    Builds a NetworkX bipartite graph showing the relationships between
    high-risk users and conflicting permissions.
    """
    # 1. Fetch data
    user_perms = engine.get_user_permissions()
    static_violations = engine.audit_static_entitlements()
    
    # Identify high-risk users and conflicting permissions to keep the graph readable
    violating_users = set()
    conflicting_perms = set()
    
    if not static_violations.empty:
        violating_users = set(static_violations["user_id"].tolist())
        
        # Get permissions causing conflicts from the rules
        conflicts = engine.rules.get("conflicting_permission_pairs", [])
        for c in conflicts:
            conflicting_perms.add(c["permission_a"])
            conflicting_perms.add(c["permission_b"])
            
    # 2. Build the Bipartite Graph
    G = nx.Graph()
    
    user_nodes = []
    perm_nodes = []
    
    # Add nodes and edges
    for _, row in user_perms.iterrows():
        user_id = row["user_id"]
        # Only render users that have violations to keep the chart clean
        if user_id not in violating_users:
            continue
            
        user_nodes.append(user_id)
        G.add_node(user_id, type="user", department=row["department"])
        
        for perm in row["permission"]:
            if perm in conflicting_perms:
                if perm not in perm_nodes:
                    perm_nodes.append(perm)
                    G.add_node(perm, type="permission")
                G.add_edge(user_id, perm)

    if len(G.nodes) == 0:
        # Create empty placeholder image if no violations found
        plt.figure(figsize=(6, 2))
        plt.text(0.5, 0.5, "No Static SoD Violations Detected", 
                 ha="center", va="center", fontsize=12, color="green")
        plt.axis("off")
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()
        return

    # 3. Setup Plot
    plt.figure(figsize=(10, 6))
    
    # Bipartite Layout: Users on the left, Permissions on the right
    pos = {}
    
    # Sort nodes for stability
    user_nodes.sort()
    perm_nodes.sort()
    
    for i, u in enumerate(user_nodes):
        pos[u] = (-1, i - len(user_nodes) / 2.0)
        
    for i, p in enumerate(perm_nodes):
        pos[p] = (1, i - len(perm_nodes) / 2.0)

    # 4. Color Code Nodes
    # Red for violating users, Orange for conflicting permissions
    node_colors = []
    node_sizes = []
    for node in G.nodes:
        if G.nodes[node]["type"] == "user":
            node_colors.append("#d9534f")  # Red
            node_sizes.append(1000)
        else:
            node_colors.append("#f0ad4e")  # Orange
            node_sizes.append(1500)

    # Draw Nodes
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes, edgecolors="#ffffff", linewidths=1.5)
    
    # Draw Edges
    nx.draw_networkx_edges(G, pos, width=1.5, edge_color="#cccccc")
    
    # Draw Labels with offsets
    labels = {node: node for node in G.nodes}
    
    # Separate label positions to prevent overlapping
    label_pos = {}
    for node, coords in pos.items():
        if G.nodes[node]["type"] == "user":
            label_pos[node] = (coords[0] - 0.25, coords[1])
        else:
            label_pos[node] = (coords[0] + 0.25, coords[1])
            
    nx.draw_networkx_labels(G, label_pos, labels=labels, font_size=10, font_weight="bold", font_family="sans-serif")

    # Titles and Legends
    plt.title("Access Conflict Matrix (Static Segregation of Duties)", fontsize=14, fontweight="bold", pad=20)
    plt.xlim(-1.8, 1.8)
    plt.ylim(-max(len(user_nodes), len(perm_nodes)) - 0.5, max(len(user_nodes), len(perm_nodes)) + 0.5)
    plt.axis("off")
    
    # Save Image
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Risk network graph saved successfully to {output_path}")

if __name__ == "__main__":
    from engine import ERPAuditEngine
    engine = ERPAuditEngine("./config/sod_rules.json", "./data")
    generate_risk_graph(engine, "./data/risk_network.png")
