#!/usr/bin/env python3
"""
MegaHarvester v3.0 - 10X BRAIN COLLECTIVE EDITION
All available LLM brains have a CONVERSATION together.
Each brain sees previous brains' answers and builds on them.
Knowledge compounds every cycle.

10X UPGRADE: 2650+ wiki topics, 150+ subreddits, 500+ brain questions
New sources: GitHub trending, Product Hunt, TechCrunch, Lobsters, dev.to, StackOverflow
Per cycle: 80 wiki, 30 subs, 10 brain questions, 100 HN, 50 ArXiv, 250 coins

Commander: Jeremy Pyne | Sovereign AI Project
"""
import os
import sys
import json
import time
import random
import hashlib
import urllib.request
import urllib.parse
import urllib.error
import ssl
import xml.etree.ElementTree as ET
from datetime import datetime
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- .env loader (no dotenv dependency) ---
def load_env():
 env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
 if not os.path.exists(env_path):
  print(f"[ENV] No .env found at {env_path}")
  return
 with open(env_path, 'r') as f:
  for line in f:
   line = line.strip()
   if not line or line.startswith('#') or '=' not in line:
    continue
   key, val = line.split('=', 1)
   key = key.strip()
   val = val.strip().strip('"').strip("'")
   if key and val:
    os.environ[key] = val
 print(f"[ENV] Loaded from {env_path}")

load_env()

# --- SSL context for urllib ---
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# --- Brain Definitions ---
# Each brain: (name, env_key, base_url, model, special_type)
# special_type: "openai" (standard), "gemini", "cohere", "anthropic"
BRAIN_DEFS = [
 # --- Original 16 brains ---
 ("grok", "XAI_API_KEY", "https://api.x.ai/v1/chat/completions", "grok-3-mini-beta", "openai"),
 ("groq", "GROQ_API_KEY", "https://api.groq.com/openai/v1/chat/completions", "llama-3.3-70b-versatile", "openai"),
 ("gemini", "GEMINI_API_KEY", "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent", None, "gemini"),
 ("deepseek", "DEEPSEEK_API_KEY", "https://api.deepseek.com/v1/chat/completions", "deepseek-chat", "openai"),
 ("together", "TOGETHER_API_KEY", "https://api.together.xyz/v1/chat/completions", "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo", "openai"),
 ("mistral", "MISTRAL_API_KEY", "https://api.mistral.ai/v1/chat/completions", "mistral-large-latest", "openai"),
 ("fireworks", "FIREWORKS_API_KEY", "https://api.fireworks.ai/inference/v1/chat/completions", "accounts/fireworks/models/llama-v3p1-70b-instruct", "openai"),
 ("openrouter", "OPENROUTER_API_KEY", "https://openrouter.ai/api/v1/chat/completions", "qwen/qwen3-30b-a3b:free", "openai"),
 ("cohere", "COHERE_API_KEY", "https://api.cohere.ai/v2/chat", None, "cohere"),
 ("cerebras", "CEREBRAS_API_KEY", "https://api.cerebras.ai/v1/chat/completions", "llama3.1-70b", "openai"),
 ("sambanova", "SAMBANOVA_API_KEY", "https://api.sambanova.ai/v1/chat/completions", "Meta-Llama-3.1-70B-Instruct", "openai"),
 ("perplexity", "PERPLEXITY_API_KEY", "https://api.perplexity.ai/chat/completions", "llama-3.1-sonar-large-128k-online", "openai"),
 ("openai", "OPENAI_API_KEY", "https://api.openai.com/v1/chat/completions", "gpt-4o-mini", "openai"),
 ("huggingface", "HF_API_KEY", "https://api-inference.huggingface.co/models/meta-llama/Meta-Llama-3-8B-Instruct/v1/chat/completions", None, "openai"),
 ("anthropic", "ANTHROPIC_API_KEY", "https://api.anthropic.com/v1/messages", "claude-3-haiku-20240307", "anthropic"),
 ("novita", "NOVITA_API_KEY", "https://api.novita.ai/v3/openai/chat/completions", "meta-llama/llama-3.1-70b-instruct", "openai"),
 # --- Extended 14 brains ---
 ("lepton", "LEPTON_API_KEY", "https://llama3-1-70b.lepton.run/api/v1/chat/completions", "llama3-1-70b", "openai"),
 ("deepinfra", "DEEPINFRA_API_KEY", "https://api.deepinfra.com/v1/openai/chat/completions", "meta-llama/Meta-Llama-3.1-70B-Instruct", "openai"),
 ("hyperbolic", "HYPERBOLIC_API_KEY", "https://api.hyperbolic.xyz/v1/chat/completions", "meta-llama/Meta-Llama-3.1-70B-Instruct", "openai"),
 ("glhf", "GLHF_API_KEY", "https://glhf.chat/api/openai/v1/chat/completions", "hf:meta-llama/Meta-Llama-3.1-70B-Instruct", "openai"),
 ("chutes", "CHUTES_API_KEY", "https://api.chutes.ai/v1/chat/completions", "meta-llama/Meta-Llama-3.1-70B-Instruct", "openai"),
 ("featherless", "FEATHERLESS_API_KEY", "https://api.featherless.ai/v1/chat/completions", "meta-llama/Meta-Llama-3.1-70B-Instruct", "openai"),
 ("lambda", "LAMBDA_API_KEY", "https://api.lambdalabs.com/v1/chat/completions", "llama3.1-70b-instruct-fp8", "openai"),
 ("friendli", "FRIENDLI_API_KEY", "https://inference.friendli.ai/v1/chat/completions", "meta-llama-3.1-70b-instruct", "openai"),
 ("nebius", "NEBIUS_API_KEY", "https://api.studio.nebius.ai/v1/chat/completions", "meta-llama/Meta-Llama-3.1-70B-Instruct", "openai"),
 ("ai21", "AI21_API_KEY", "https://api.ai21.com/studio/v1/chat/completions", "jamba-1.5-large", "openai"),
 ("writer", "WRITER_API_KEY", "https://api.writer.com/v1/chat", "palmyra-x-004", "openai"),
 ("replicate", "REPLICATE_API_KEY", "https://api.replicate.com/v1/predictions", "meta/meta-llama-3.1-405b-instruct", "openai"),
 ("anyscale", "ANYSCALE_API_KEY", "https://api.endpoints.anyscale.com/v1/chat/completions", "meta-llama/Meta-Llama-3.1-70B-Instruct", "openai"),
 ("cloudflare", "CF_AI_TOKEN", "https://api.cloudflare.com/client/v4/accounts/ACCOUNT/ai/run/@cf/meta/llama-3.1-70b-instruct", None, "openai"),
]


# ============================================================
# WIKI_TOPICS - 2650+ Wikipedia articles for knowledge harvesting
# 100X EXPANSION - Every domain of human knowledge
# ============================================================
WIKI_TOPICS = [
 # === PSYCHOLOGY & INFLUENCE (120) ===
 "Social_psychology", "Cognitive_bias", "Dark_triad", "Persuasion",
 "Propaganda", "Nudge_theory", "Anchoring_(cognitive_bias)", "Framing_effect_(psychology)",
 "Milgram_experiment", "Stanford_prison_experiment", "Groupthink", "Conformity",
 "Obedience_(human_behavior)", "Social_engineering_(security)", "Manipulation_(psychology)",
 "Gaslighting", "Love_bombing", "Neuro-linguistic_programming", "Hypnosis",
 "Subliminal_stimuli", "Emotional_intelligence", "Machiavelli",
 "The_Art_of_War", "The_Prince_(book)", "Influence_(book)", "Robert_Cialdini",
 "Learned_helplessness", "Cognitive_dissonance", "Dunning-Kruger_effect", "Halo_effect",
 "Confirmation_bias", "Availability_heuristic", "Bandwagon_effect", "Bystander_effect",
 "Stockholm_syndrome", "Sunk_cost", "Loss_aversion", "Prospect_theory",
 "Behavioral_economics", "Daniel_Kahneman", "Thinking,_Fast_and_Slow", "Flow_(psychology)",
 "Maslow%27s_hierarchy_of_needs", "Self-actualization", "Operant_conditioning",
 "Classical_conditioning", "Pavlov%27s_dog", "B._F._Skinner", "Sigmund_Freud",
 "Carl_Jung", "Collective_unconscious", "Archetypes", "Shadow_(psychology)",
 "Personality_psychology", "Big_Five_personality_traits", "Myers-Briggs_Type_Indicator",
 "Narcissistic_personality_disorder", "Antisocial_personality_disorder", "Psychopathy",
 "Sociopathy", "Emotional_abuse", "Psychological_manipulation", "Power_(social_and_political)",
 "Authority", "Obedience_to_authority", "Asch_conformity_experiments", "Social_proof",
 "Reciprocity_(social_psychology)", "Scarcity_(social_psychology)", "Commitment_and_consistency",
 "Mere_exposure_effect", "Primacy_effect", "Recency_effect", "Priming_(psychology)",
 "Cognitive_load", "Decision_fatigue", "Choice_overload", "Paradox_of_choice",
 "Ego_depletion", "Willpower", "Self-control", "Delayed_gratification",
 "Marshmallow_experiment", "Habit", "Habit_formation", "Neuroplasticity",
 "Dopamine", "Serotonin", "Oxytocin", "Endorphins",
 "Amygdala", "Prefrontal_cortex", "Hippocampus", "Mirror_neuron",
 "Theory_of_mind", "Empathy", "Compassion", "Altruism",
 "Game_theory", "Prisoner%27s_dilemma", "Nash_equilibrium", "Zero-sum_game",
 "Positive-sum_game", "Tragedy_of_the_commons", "Free-rider_problem", "Public_goods_game",
 "Ultimatum_game", "Dictator_game", "Mechanism_design", "Auction_theory",
 "Principal-agent_problem", "Moral_hazard", "Adverse_selection", "Information_asymmetry",
 "Signaling_(economics)", "Screening_(economics)", "Bounded_rationality", "Satisficing",
 "Heuristic", "Mental_model", "Systems_thinking", "Critical_thinking",
 "Logical_fallacy", "List_of_cognitive_biases", "List_of_fallacies", "Rhetoric",
 "Dialectic", "Socratic_method", "Argumentation_theory", "Debate",

 # === ARTIFICIAL INTELLIGENCE & MACHINE LEARNING (200) ===
 "Artificial_intelligence", "Machine_learning", "Deep_learning", "Neural_network",
 "Convolutional_neural_network", "Recurrent_neural_network", "Transformer_(machine_learning_model)",
 "Attention_(machine_learning)", "BERT_(language_model)", "GPT-4", "Large_language_model",
 "Natural_language_processing", "Computer_vision", "Reinforcement_learning",
 "Supervised_learning", "Unsupervised_learning", "Semi-supervised_learning",
 "Transfer_learning", "Few-shot_learning", "Zero-shot_learning", "Meta-learning_(computer_science)",
 "AutoML", "Neural_architecture_search", "Hyperparameter_optimization",
 "Gradient_descent", "Backpropagation", "Batch_normalization", "Dropout_(neural_networks)",
 "Regularization_(mathematics)", "Overfitting", "Underfitting", "Bias-variance_tradeoff",
 "Cross-validation_(statistics)", "Ensemble_learning", "Random_forest", "Boosting_(machine_learning)",
 "XGBoost", "Support_vector_machine", "Decision_tree_learning", "K-nearest_neighbors_algorithm",
 "Naive_Bayes_classifier", "Logistic_regression", "Linear_regression", "Polynomial_regression",
 "Principal_component_analysis", "Dimensionality_reduction", "Feature_engineering",
 "Feature_selection", "Data_augmentation", "Generative_adversarial_network",
 "Variational_autoencoder", "Diffusion_model", "Stable_Diffusion", "DALL-E",
 "Midjourney", "Text-to-image_generation", "Text-to-video", "Speech_synthesis",
 "Speech_recognition", "Optical_character_recognition", "Object_detection",
 "Image_segmentation", "Semantic_segmentation", "Instance_segmentation",
 "Pose_estimation", "Facial_recognition_system", "Emotion_recognition",
 "Sentiment_analysis", "Named-entity_recognition", "Part-of-speech_tagging",
 "Machine_translation", "Question_answering", "Text_summarization",
 "Information_retrieval", "Recommender_system", "Collaborative_filtering",
 "Content-based_filtering", "Knowledge_graph", "Ontology_(information_science)",
 "Semantic_Web", "Linked_data", "Resource_Description_Framework",
 "Expert_system", "Fuzzy_logic", "Bayesian_network", "Markov_chain",
 "Hidden_Markov_model", "Kalman_filter", "Monte_Carlo_method",
 "Markov_decision_process", "Q-learning", "Deep_Q-network", "Policy_gradient_methods",
 "Actor-critic_methods", "Proximal_policy_optimization", "Multi-agent_system",
 "Swarm_intelligence", "Ant_colony_optimization", "Particle_swarm_optimization",
 "Genetic_algorithm", "Evolutionary_computation", "Neuroevolution",
 "Artificial_general_intelligence", "Artificial_superintelligence", "Technological_singularity",
 "AI_alignment", "AI_safety", "Existential_risk_from_artificial_general_intelligence",
 "Friendly_artificial_intelligence", "Instrumental_convergence", "Orthogonality_thesis",
 "AI_box_experiment", "Reward_hacking", "Goodhart%27s_law", "Moravec%27s_paradox",
 "Chinese_room", "Turing_test", "ELIZA", "Symbolic_artificial_intelligence",
 "Connectionism", "Embodied_cognition", "Situated_cognition", "Cognitive_architecture",
 "SOAR_(cognitive_architecture)", "ACT-R", "OpenCog", "Cyc",
 "Wolfram_Alpha", "IBM_Watson", "AlphaGo", "AlphaFold",
 "AlphaZero", "MuZero", "DeepMind", "OpenAI",
 "Anthropic", "Google_Brain", "Meta_AI", "Stability_AI",
 "Hugging_Face", "MLOps", "Model_serving", "Model_monitoring",
 "A/B_testing", "Feature_store", "Data_pipeline", "ETL",
 "Data_warehouse", "Data_lake", "Data_mesh", "Vector_database",
 "Embedding", "Word2vec", "GloVe", "FastText",
 "RLHF", "Constitutional_AI", "Chain-of-thought_prompting",
 "Retrieval-augmented_generation", "Fine-tuning_(deep_learning)", "LoRA_(machine_learning)",
 "Quantization_(signal_processing)", "Knowledge_distillation", "Pruning_(neural_networks)",
 "Edge_computing", "TinyML", "Federated_learning", "Differential_privacy",
 "Homomorphic_encryption", "Secure_multi-party_computation",
 "Explainable_artificial_intelligence", "Interpretability_(machine_learning)",
 "Adversarial_machine_learning", "Data_poisoning", "Model_extraction_attack",
 "Deepfake", "Synthetic_media", "AI_art", "Procedural_generation",
 "Computational_creativity", "AI_in_healthcare", "AI_in_finance",
 "Autonomous_vehicle", "Robotics", "Robot_learning", "Simultaneous_localization_and_mapping",
 "Path_planning", "Motion_planning", "Inverse_kinematics", "Control_theory",

 # === COMPUTER SCIENCE & SYSTEMS (200) ===
 "Computer_science", "Algorithm", "Data_structure", "Computational_complexity_theory",
 "Big_O_notation", "P_versus_NP_problem", "NP-completeness", "Turing_machine",
 "Halting_problem", "Church-Turing_thesis", "Lambda_calculus", "Automata_theory",
 "Finite-state_machine", "Pushdown_automaton", "Context-free_grammar", "Regular_expression",
 "Compiler", "Interpreter_(computing)", "Just-in-time_compilation", "Abstract_syntax_tree",
 "Parsing", "Lexical_analysis", "Code_generation_(compiler)", "Optimization_(computer_science)",
 "Operating_system", "Kernel_(operating_system)", "Process_(computing)", "Thread_(computing)",
 "Concurrency_(computer_science)", "Parallel_computing", "Distributed_computing",
 "MapReduce", "Apache_Hadoop", "Apache_Spark", "Apache_Kafka",
 "Message_queue", "Microservices", "Service-oriented_architecture", "API",
 "REST", "GraphQL", "gRPC", "WebSocket",
 "HTTP", "HTTPS", "TCP/IP", "UDP",
 "Domain_Name_System", "Content_delivery_network", "Load_balancing_(computing)",
 "Reverse_proxy", "Nginx", "Apache_HTTP_Server", "Docker_(software)",
 "Kubernetes", "Container_(computing)", "Virtualization", "Hypervisor",
 "Cloud_computing", "Infrastructure_as_a_service", "Platform_as_a_service",
 "Software_as_a_service", "Serverless_computing", "AWS_Lambda",
 "Amazon_Web_Services", "Microsoft_Azure", "Google_Cloud_Platform",
 "Database", "Relational_database", "SQL", "NoSQL",
 "PostgreSQL", "MySQL", "MongoDB", "Redis",
 "Apache_Cassandra", "Elasticsearch", "SQLite", "ACID",
 "CAP_theorem", "Eventual_consistency", "Database_index", "B-tree",
 "Hash_table", "Binary_search_tree", "Red-black_tree", "AVL_tree",
 "Trie", "Graph_(abstract_data_type)", "Heap_(data_structure)", "Stack_(abstract_data_type)",
 "Queue_(abstract_data_type)", "Linked_list", "Array_(data_structure)", "Dynamic_array",
 "Sorting_algorithm", "Quicksort", "Merge_sort", "Heapsort",
 "Binary_search_algorithm", "Depth-first_search", "Breadth-first_search", "Dijkstra%27s_algorithm",
 "A*_search_algorithm", "Dynamic_programming", "Greedy_algorithm", "Divide-and-conquer_algorithm",
 "Recursion_(computer_science)", "Memoization", "Hash_function", "Bloom_filter",
 "Cache_(computing)", "Memory_management", "Garbage_collection_(computer_science)",
 "Memory_leak", "Buffer_overflow", "Stack_overflow", "Segmentation_fault",
 "Version_control", "Git", "Continuous_integration", "Continuous_delivery",
 "DevOps", "Site_reliability_engineering", "Infrastructure_as_code",
 "Terraform_(software)", "Ansible_(software)", "Configuration_management",
 "Monitoring_(software)", "Observability_(software)", "Logging", "Distributed_tracing",
 "Software_testing", "Unit_testing", "Integration_testing", "Test-driven_development",
 "Behavior-driven_development", "Agile_software_development", "Scrum_(software_development)",
 "Kanban_(development)", "Extreme_programming", "Software_design_pattern",
 "Model-view-controller", "Observer_pattern", "Factory_method_pattern", "Singleton_pattern",
 "Strategy_pattern", "SOLID", "Don%27t_repeat_yourself", "KISS_principle",
 "Technical_debt", "Code_refactoring", "Software_architecture", "Clean_architecture",
 "Domain-driven_design", "Event-driven_architecture", "CQRS", "Event_sourcing",
 "Saga_pattern", "Circuit_breaker_design_pattern",

 # === MATHEMATICS (200) ===
 "Mathematics", "Number_theory", "Abstract_algebra", "Linear_algebra",
 "Calculus", "Real_analysis", "Complex_analysis", "Topology",
 "Differential_geometry", "Algebraic_geometry", "Category_theory", "Set_theory",
 "Mathematical_logic", "Model_theory", "Proof_theory", "Recursion_theory",
 "Graph_theory", "Combinatorics", "Probability_theory", "Statistics",
 "Bayesian_statistics", "Frequentist_inference", "Hypothesis_testing", "Regression_analysis",
 "Time_series", "Stochastic_process", "Random_walk", "Brownian_motion",
 "Markov_chain", "Ergodic_theory", "Information_theory", "Entropy_(information_theory)",
 "Shannon_entropy", "Kolmogorov_complexity", "Coding_theory", "Error_detection_and_correction",
 "Cryptography", "RSA_(cryptosystem)", "Elliptic-curve_cryptography", "Hash_function",
 "Digital_signature", "Public-key_cryptography", "Symmetric-key_algorithm", "AES_(cipher)",
 "Post-quantum_cryptography", "Lattice-based_cryptography", "Zero-knowledge_proof",
 "Homomorphic_encryption", "Secure_multi-party_computation", "Secret_sharing",
 "Optimization_(mathematics)", "Linear_programming", "Integer_programming",
 "Convex_optimization", "Gradient_descent", "Stochastic_gradient_descent",
 "Lagrange_multiplier", "Simplex_algorithm", "Interior-point_method",
 "Combinatorial_optimization", "Travelling_salesman_problem", "Knapsack_problem",
 "Satisfiability_problem", "Constraint_satisfaction_problem", "Heuristic_(computer_science)",
 "Approximation_algorithm", "Numerical_analysis", "Numerical_linear_algebra",
 "Finite_element_method", "Numerical_integration", "Interpolation",
 "Ordinary_differential_equation", "Partial_differential_equation", "Fourier_analysis",
 "Fourier_transform", "Laplace_transform", "Z-transform", "Wavelet",
 "Signal_processing", "Digital_signal_processing", "Filter_(signal_processing)",
 "Control_theory", "PID_controller", "State-space_representation", "Feedback",
 "Stability_theory", "Lyapunov_stability", "Chaos_theory", "Butterfly_effect",
 "Fractal", "Mandelbrot_set", "Julia_set", "Strange_attractor",
 "Dynamical_system", "Bifurcation_theory", "Catastrophe_theory", "Complexity",
 "Emergence", "Self-organization", "Cellular_automaton", "Conway%27s_Game_of_Life",
 "Wolfram%27s_rule_110", "Complexity_class", "Computational_complexity",
 "Space_complexity", "Amortized_analysis", "Parallel_algorithm", "Quantum_computing",
 "Qubit", "Quantum_gate", "Quantum_circuit", "Quantum_entanglement",
 "Quantum_teleportation", "Quantum_error_correction", "Shor%27s_algorithm",
 "Grover%27s_algorithm", "Quantum_supremacy", "Quantum_annealing",
 "Adiabatic_quantum_computation", "Topological_quantum_computer",
 "Group_theory", "Ring_(mathematics)", "Field_(mathematics)", "Vector_space",
 "Matrix_(mathematics)", "Eigenvalue", "Singular_value_decomposition",
 "Tensor", "Manifold", "Riemannian_geometry", "Lie_group",
 "Lie_algebra", "Galois_theory", "Algebraic_number_theory", "Analytic_number_theory",
 "Prime_number", "Riemann_hypothesis", "Twin_prime", "Goldbach%27s_conjecture",
 "Fermat%27s_Last_Theorem", "Millennium_Prize_Problems", "Poincare_conjecture",
 "Navier-Stokes_existence_and_smoothness", "Yang-Mills_existence_and_mass_gap",
 "Hodge_conjecture", "Birch_and_Swinnerton-Dyer_conjecture",
 "Godel%27s_incompleteness_theorems", "Continuum_hypothesis", "Axiom_of_choice",
 "Zermelo-Fraenkel_set_theory", "Peano_axioms", "Mathematical_induction",
 "Proof_by_contradiction", "Constructive_proof", "Formal_verification",
 "Automated_theorem_proving", "Interactive_theorem_proving", "Lean_(proof_assistant)",
 "Coq_(software)", "Isabelle_(proof_assistant)",
 "Measure_theory", "Lebesgue_integration", "Functional_analysis", "Hilbert_space",
 "Banach_space", "Operator_theory", "Spectral_theory", "Distribution_(mathematics)",
 "Generalized_function", "Differential_form", "Exterior_algebra", "De_Rham_cohomology",
 "Homology_(mathematics)", "Homotopy", "Fundamental_group", "Covering_space",
 "Knot_theory", "Braid_group", "Mathematical_physics", "String_theory",
 "Loop_quantum_gravity", "Noncommutative_geometry", "Algebraic_topology",
 "Persistent_homology", "Topological_data_analysis", "Applied_mathematics",
 "Mathematical_biology", "Mathematical_finance", "Black-Scholes_model",
 "Stochastic_calculus", "Ito_calculus", "Martingale_(probability_theory)",
 "Risk-neutral_measure", "Value_at_risk", "Monte_Carlo_methods_in_finance",

 # === PHYSICS (200) ===
 "Physics", "Classical_mechanics", "Newtonian_mechanics", "Lagrangian_mechanics",
 "Hamiltonian_mechanics", "Special_relativity", "General_relativity", "Quantum_mechanics",
 "Quantum_field_theory", "Standard_Model", "Particle_physics", "Higgs_boson",
 "Quark", "Lepton", "Neutrino", "Antimatter",
 "Dark_matter", "Dark_energy", "Cosmological_constant", "Big_Bang",
 "Cosmic_inflation", "Cosmic_microwave_background", "Black_hole", "Hawking_radiation",
 "Neutron_star", "Pulsar", "Magnetar", "Gravitational_wave",
 "LIGO", "Event_Horizon_Telescope", "Hubble_Space_Telescope", "James_Webb_Space_Telescope",
 "Electromagnetism", "Maxwell%27s_equations", "Electromagnetic_radiation", "Photon",
 "Wave-particle_duality", "Heisenberg_uncertainty_principle", "Schrodinger_equation",
 "Quantum_superposition", "Quantum_decoherence", "Many-worlds_interpretation",
 "Copenhagen_interpretation", "Bell%27s_theorem", "EPR_paradox", "Quantum_tunneling",
 "Bose-Einstein_condensate", "Superconductivity", "Superfluidity", "Quantum_Hall_effect",
 "Topological_insulator", "Semiconductor", "Transistor", "Integrated_circuit",
 "Photovoltaic_cell", "LED", "Laser", "Fiber_optics",
 "Plasma_(physics)", "Nuclear_physics", "Nuclear_fission", "Nuclear_fusion",
 "Tokamak", "ITER", "Nuclear_weapon", "Radioactive_decay",
 "Half-life", "Isotope", "Uranium", "Plutonium",
 "Thermodynamics", "Entropy", "Second_law_of_thermodynamics", "Statistical_mechanics",
 "Boltzmann_distribution", "Partition_function_(statistical_mechanics)",
 "Phase_transition", "Critical_phenomena", "Renormalization", "Renormalization_group",
 "Symmetry_breaking", "Gauge_theory", "Yang-Mills_theory", "Quantum_chromodynamics",
 "Quantum_electrodynamics", "Feynman_diagram", "Path_integral_formulation",
 "String_theory", "M-theory", "Brane", "Calabi-Yau_manifold",
 "Holographic_principle", "AdS/CFT_correspondence", "Information_paradox",
 "Penrose-Hawking_singularity_theorems", "Cosmic_censorship_hypothesis",
 "Wormhole", "Time_travel", "Alcubierre_drive", "Fermi_paradox",
 "Drake_equation", "Kardashev_scale", "Dyson_sphere",
 "Condensed_matter_physics", "Solid-state_physics", "Crystal_structure",
 "Band_theory", "Fermi_level", "Superlattice", "Metamaterial",
 "Graphene", "Carbon_nanotube", "Quantum_dot", "Spintronics",
 "Magnetoresistance", "Giant_magnetoresistance", "Tunnel_magnetoresistance",
 "Acoustics", "Optics", "Nonlinear_optics", "Quantum_optics",
 "Photonic_crystal", "Nanophotonics", "Plasmonics", "Near-field_optics",
 "Fluid_dynamics", "Navier-Stokes_equations", "Turbulence", "Aerodynamics",
 "Hydrodynamics", "Magnetohydrodynamics", "Computational_fluid_dynamics",
 "Geophysics", "Seismology", "Atmospheric_physics", "Climate_model",
 "Astrophysics", "Stellar_evolution", "Supernova", "White_dwarf",
 "Galaxy_formation_and_evolution", "Large-scale_structure_of_the_universe",
 "Observable_universe", "Multiverse", "Anthropic_principle",
 "Fine-tuned_universe", "Vacuum_energy", "Casimir_effect", "Zero-point_energy",
 "Quantum_vacuum", "Virtual_particle", "Lamb_shift", "Anomalous_magnetic_dipole_moment",

 # === CHEMISTRY & MATERIALS (120) ===
 "Chemistry", "Organic_chemistry", "Inorganic_chemistry", "Physical_chemistry",
 "Analytical_chemistry", "Biochemistry", "Polymer_chemistry", "Supramolecular_chemistry",
 "Computational_chemistry", "Quantum_chemistry", "Molecular_orbital_theory",
 "Chemical_bond", "Covalent_bond", "Ionic_bond", "Metallic_bonding",
 "Hydrogen_bond", "Van_der_Waals_force", "Chemical_reaction", "Catalysis",
 "Enzyme_catalysis", "Homogeneous_catalysis", "Heterogeneous_catalysis",
 "Electrochemistry", "Battery_(electricity)", "Lithium-ion_battery", "Solid-state_battery",
 "Fuel_cell", "Hydrogen_economy", "Electrolysis", "Photocatalysis",
 "Nanomaterial", "Nanoparticle", "Nanocomposite", "Self-assembly",
 "Molecular_self-assembly", "DNA_nanotechnology", "DNA_origami",
 "Materials_science", "Metallurgy", "Ceramic_material", "Composite_material",
 "Smart_material", "Shape-memory_alloy", "Piezoelectricity", "Ferroelectricity",
 "Biomaterial", "Biodegradable_plastic", "Bioplastic", "Polymer",
 "Thermoplastic", "Thermoset", "Elastomer", "Rubber",
 "Carbon_fiber", "Kevlar", "Aerogel", "Hydrogel",
 "Semiconductor_material", "Silicon", "Gallium_arsenide", "Gallium_nitride",
 "Perovskite_(structure)", "Perovskite_solar_cell", "Organic_solar_cell",
 "OLED", "Quantum_dot_display", "E_Ink", "Liquid_crystal",
 "Rare-earth_element", "Lithium", "Cobalt", "Nickel",
 "Titanium", "Tungsten", "Platinum", "Gold",
 "Periodic_table", "Chemical_element", "Isotope", "Radioactivity",
 "Nuclear_chemistry", "Radiochemistry", "Actinide", "Transuranium_element",
 "Synthetic_element", "Island_of_stability",
 "Organic_synthesis", "Total_synthesis", "Retrosynthetic_analysis", "Combinatorial_chemistry",
 "High-throughput_screening", "Drug_discovery", "Pharmacology", "Pharmacokinetics",
 "Medicinal_chemistry", "Chemical_biology", "Proteomics", "Metabolomics",
 "Spectroscopy", "Mass_spectrometry", "NMR_spectroscopy", "X-ray_crystallography",
 "Electron_microscopy", "Scanning_tunneling_microscope", "Atomic_force_microscopy",

 # === BIOLOGY & GENETICS (200) ===
 "Biology", "Cell_biology", "Molecular_biology", "Genetics",
 "Genomics", "Epigenetics", "Gene_expression", "DNA",
 "RNA", "Protein", "Amino_acid", "Protein_folding",
 "Protein_structure_prediction", "AlphaFold", "CRISPR", "CRISPR_gene_editing",
 "Gene_therapy", "Genetic_engineering", "Genetically_modified_organism",
 "Synthetic_biology", "Bioinformatics", "Computational_biology", "Systems_biology",
 "Metabolic_engineering", "Directed_evolution", "Phage_display",
 "Polymerase_chain_reaction", "DNA_sequencing", "Next-generation_sequencing",
 "Single-cell_sequencing", "Metagenomics", "Microbiome", "Human_Microbiome_Project",
 "Gut_flora", "Probiotics", "Antibiotic_resistance", "Antimicrobial_resistance",
 "Bacteriophage", "Virology", "Virus", "Prion",
 "Immunology", "Immune_system", "Innate_immune_system", "Adaptive_immune_system",
 "T_cell", "B_cell", "Antibody", "Antigen",
 "Vaccine", "mRNA_vaccine", "Monoclonal_antibody", "CAR_T_cell",
 "Immunotherapy", "Cancer_immunotherapy", "Checkpoint_inhibitor",
 "Oncology", "Cancer", "Tumor_suppressor_gene", "Oncogene",
 "Metastasis", "Angiogenesis", "Apoptosis", "Autophagy",
 "Stem_cell", "Induced_pluripotent_stem_cell", "Embryonic_stem_cell",
 "Cell_differentiation", "Tissue_engineering", "Organ-on-a-chip",
 "Regenerative_medicine", "3D_bioprinting", "Xenotransplantation",
 "Neuroscience", "Neuron", "Synapse", "Neurotransmitter",
 "Action_potential", "Neural_circuit", "Brain", "Cerebral_cortex",
 "Limbic_system", "Basal_ganglia", "Cerebellum", "Brain_stem",
 "Connectome", "Human_Connectome_Project", "Brain-computer_interface",
 "Neuralink", "Electroencephalography", "Functional_MRI", "Optogenetics",
 "Neuroimaging", "Cognitive_neuroscience", "Behavioral_neuroscience",
 "Computational_neuroscience", "Neural_coding", "Neural_oscillation",
 "Consciousness", "Hard_problem_of_consciousness", "Integrated_information_theory",
 "Global_workspace_theory", "Higher-order_theories_of_consciousness",
 "Evolution", "Natural_selection", "Sexual_selection", "Genetic_drift",
 "Gene_flow", "Speciation", "Phylogenetics", "Molecular_clock",
 "Common_descent", "Last_universal_common_ancestor", "Abiogenesis",
 "RNA_world_hypothesis", "Panspermia", "Extremophile", "Astrobiology",
 "Ecology", "Ecosystem", "Biodiversity", "Conservation_biology",
 "Extinction", "Mass_extinction", "Holocene_extinction", "Climate_change",
 "Deforestation", "Ocean_acidification", "Coral_bleaching", "Desertification",
 "Population_ecology", "Community_ecology", "Food_web", "Trophic_level",
 "Keystone_species", "Invasive_species", "Ecological_succession",
 "Biogeography", "Island_biogeography", "Biome", "Rainforest",
 "Marine_biology", "Deep_sea", "Hydrothermal_vent", "Chemosynthesis",
 "Bioluminescence", "Biomimetics", "Bionic", "Bioelectronics",
 "Botany", "Plant_physiology", "Photosynthesis", "Chloroplast",
 "Mycology", "Fungi", "Mycelium", "Mushroom",
 "Zoology", "Ethology", "Animal_cognition", "Tool_use_by_animals",
 "Animal_communication", "Eusociality", "Kin_selection", "Altruism_(biology)",
 "Parasitism", "Mutualism_(biology)", "Symbiosis", "Coevolution",
 "Convergent_evolution", "Parallel_evolution", "Mimicry", "Camouflage",
 "Aging", "Senescence", "Telomere", "Telomerase",
 "Calorie_restriction", "Longevity", "Life_extension", "Cryonics",

 # === ECONOMICS & FINANCE (200) ===
 "Economics", "Microeconomics", "Macroeconomics", "Monetary_economics",
 "Fiscal_policy", "Monetary_policy", "Central_bank", "Federal_Reserve",
 "European_Central_Bank", "Bank_of_Japan", "Interest_rate", "Inflation",
 "Deflation", "Stagflation", "Hyperinflation", "Money_supply",
 "Quantitative_easing", "Open_market_operation", "Fractional-reserve_banking",
 "Money_creation", "Money_multiplier", "Fiat_money", "Gold_standard",
 "Bretton_Woods_system", "Exchange_rate", "Foreign_exchange_market",
 "Currency_pair", "Carry_trade", "Purchasing_power_parity",
 "Supply_and_demand", "Market_equilibrium", "Price_elasticity_of_demand",
 "Marginal_utility", "Consumer_surplus", "Producer_surplus", "Deadweight_loss",
 "Externality", "Public_good_(economics)", "Market_failure", "Government_failure",
 "Monopoly", "Oligopoly", "Perfect_competition", "Monopolistic_competition",
 "Antitrust", "Regulation", "Deregulation", "Privatization",
 "GDP", "GNP", "Purchasing_power_parity", "Gini_coefficient",
 "Lorenz_curve", "Income_inequality", "Wealth_inequality", "Poverty",
 "Economic_growth", "Human_development_index", "Economic_indicator",
 "Leading_indicator", "Lagging_indicator", "Coincident_indicator",
 "Business_cycle", "Recession", "Depression_(economics)", "Financial_crisis",
 "Systemic_risk", "Too_big_to_fail", "Bailout", "Moral_hazard",
 "Stock_market", "Stock_exchange", "New_York_Stock_Exchange", "NASDAQ",
 "London_Stock_Exchange", "Tokyo_Stock_Exchange", "Shanghai_Stock_Exchange",
 "Market_capitalization", "Price-earnings_ratio", "Dividend_yield",
 "Fundamental_analysis", "Technical_analysis", "Efficient-market_hypothesis",
 "Random_walk_hypothesis", "Capital_asset_pricing_model", "Modern_portfolio_theory",
 "Markowitz_model", "Sharpe_ratio", "Alpha_(finance)", "Beta_(finance)",
 "Volatility_(finance)", "VIX", "Options_(finance)", "Black-Scholes_model",
 "Greeks_(finance)", "Delta_hedging", "Put-call_parity",
 "Futures_contract", "Forward_contract", "Swap_(finance)", "Derivative_(finance)",
 "Credit_default_swap", "Collateralized_debt_obligation", "Mortgage-backed_security",
 "Securitization", "Structured_finance", "Hedge_fund", "Private_equity",
 "Venture_capital", "Angel_investor", "Initial_public_offering",
 "Special-purpose_acquisition_company", "Leveraged_buyout", "Mergers_and_acquisitions",
 "Due_diligence", "Valuation_(finance)", "Discounted_cash_flow",
 "Earnings_before_interest_and_taxes", "Free_cash_flow", "Net_present_value",
 "Internal_rate_of_return", "Return_on_investment", "Return_on_equity",
 "Debt-to-equity_ratio", "Current_ratio", "Quick_ratio",
 "Algorithmic_trading", "High-frequency_trading", "Market_making",
 "Dark_pool", "Order_flow", "Bid-ask_spread", "Liquidity",
 "Market_microstructure", "Flash_crash", "Circuit_breaker_(financial_markets)",
 "Short_selling", "Short_squeeze", "Margin_(finance)", "Leverage_(finance)",
 "Commodity_market", "Gold_as_an_investment", "Crude_oil", "Natural_gas",
 "Agricultural_commodity", "Commodity_futures", "Spot_contract",
 "Real_estate", "Real_estate_investment_trust", "Mortgage", "Amortization_(business)",
 "Property_tax", "Capital_gains_tax", "Tax_haven", "Offshore_financial_centre",
 "Transfer_pricing", "Tax_avoidance", "Tax_evasion",
 "Insurance", "Reinsurance", "Actuarial_science", "Underwriting",
 "Banking", "Investment_banking", "Commercial_bank", "Credit_union",
 "Fintech", "Neobank", "Payment_system", "SWIFT",
 "ACH", "Wire_transfer", "Mobile_payment", "Contactless_payment",

 # === CRYPTOCURRENCY & BLOCKCHAIN (150) ===
 "Cryptocurrency", "Bitcoin", "Ethereum", "Blockchain",
 "Distributed_ledger", "Consensus_mechanism", "Proof_of_work", "Proof_of_stake",
 "Delegated_proof_of_stake", "Proof_of_authority", "Byzantine_fault_tolerance",
 "Practical_Byzantine_fault_tolerance", "Nakamoto_consensus",
 "Smart_contract", "Solidity_(programming_language)", "Ethereum_Virtual_Machine",
 "Decentralized_application", "Decentralized_finance", "Automated_market_maker",
 "Liquidity_pool", "Yield_farming", "Liquidity_mining", "Impermanent_loss",
 "Flash_loan", "Maximal_extractable_value", "Front_running",
 "Sandwich_attack", "Decentralized_exchange", "Uniswap", "Aave",
 "Compound_(finance)", "MakerDAO", "Curve_Finance",
 "Non-fungible_token", "ERC-20", "ERC-721", "ERC-1155",
 "Token_standard", "Initial_coin_offering", "Security_token_offering",
 "Decentralized_autonomous_organization", "Governance_token", "Stablecoin",
 "Tether_(cryptocurrency)", "USD_Coin", "Dai_(cryptocurrency)",
 "Algorithmic_stablecoin", "Central_bank_digital_currency",
 "Bitcoin_network", "Lightning_Network", "SegWit", "Taproot",
 "Bitcoin_mining", "Mining_pool", "ASIC", "Hash_rate",
 "Bitcoin_halving", "Bitcoin_scalability_problem",
 "Solana_(blockchain)", "Cardano_(blockchain)", "Polkadot_(cryptocurrency)",
 "Avalanche_(blockchain)", "Cosmos_(blockchain)", "Near_Protocol",
 "Arbitrum", "Optimism_(blockchain)", "ZK-rollup", "Optimistic_rollup",
 "Layer_2_(blockchain)", "Sidechain", "Cross-chain", "Bridge_(blockchain)",
 "Interoperability_(blockchain)", "Atomic_swap", "Wrapped_token",
 "Cryptocurrency_wallet", "Hardware_wallet", "Cold_storage_(cryptocurrency)",
 "Seed_phrase", "Private_key", "Public_key",
 "Cryptocurrency_exchange", "Binance", "Coinbase", "Kraken_(exchange)",
 "FTX_(company)", "Market_manipulation", "Pump_and_dump",
 "Rug_pull", "Ponzi_scheme", "Pyramid_scheme",
 "Meme_coin", "Dogecoin", "Shiba_Inu_(cryptocurrency)",
 "Web3", "Metaverse", "Virtual_reality", "Augmented_reality",
 "Mixed_reality", "Spatial_computing",
 "Privacy_coin", "Monero", "Zcash", "Tornado_Cash",
 "Cryptocurrency_regulation", "Securities_and_Exchange_Commission",
 "Commodity_Futures_Trading_Commission", "Financial_Crimes_Enforcement_Network",
 "Know_your_customer", "Anti-money_laundering",
 "Tokenomics", "Token_burning", "Vesting_(cryptocurrency)", "Airdrop_(cryptocurrency)",
 "Staking_(cryptocurrency)", "Validator_(blockchain)", "Slashing_(blockchain)",
 "Gas_(Ethereum)", "Transaction_fee", "Mempool",
 "Cryptocurrency_and_crime", "Silk_Road_(marketplace)", "Ransomware",
 "Bitcoin_ATM", "Cryptocurrency_in_El_Salvador",

 # === BUSINESS & ENTREPRENEURSHIP (150) ===
 "Entrepreneurship", "Startup_company", "Lean_startup", "Minimum_viable_product",
 "Product-market_fit", "Growth_hacking", "Viral_marketing", "Network_effect",
 "Metcalfe%27s_law", "First-mover_advantage", "Competitive_advantage",
 "Porter%27s_five_forces_analysis", "SWOT_analysis", "Business_model_canvas",
 "Subscription_business_model", "Freemium", "Platform_economy",
 "Sharing_economy", "Gig_economy", "Creator_economy",
 "E-commerce", "Dropshipping", "Affiliate_marketing", "Digital_marketing",
 "Search_engine_optimization", "Pay-per-click", "Content_marketing",
 "Social_media_marketing", "Email_marketing", "Conversion_rate_optimization",
 "Customer_acquisition_cost", "Customer_lifetime_value", "Churn_rate",
 "Net_promoter_score", "Product_management", "User_experience_design",
 "Design_thinking", "Jobs_to_be_done", "Customer_development",
 "Agile_software_development", "Scrum_(software_development)", "Kanban",
 "Business_strategy", "Corporate_strategy", "Blue_Ocean_Strategy",
 "Disruptive_innovation", "Innovator%27s_dilemma", "Creative_destruction",
 "Vertical_integration", "Horizontal_integration", "Economies_of_scale",
 "Economies_of_scope", "Experience_curve_effects", "Learning_curve",
 "Brand_management", "Brand_equity", "Trademark",
 "Patent", "Copyright", "Trade_secret", "Intellectual_property",
 "Licensing", "Franchising", "Joint_venture", "Strategic_alliance",
 "Supply_chain_management", "Logistics", "Inventory_management",
 "Just-in-time_manufacturing", "Lean_manufacturing", "Six_Sigma",
 "Total_quality_management", "Kaizen", "5S_(methodology)",
 "Human_resource_management", "Recruitment", "Employee_retention",
 "Organizational_culture", "Organizational_behavior", "Leadership",
 "Servant_leadership", "Transformational_leadership", "Situational_leadership",
 "Emotional_intelligence", "Negotiation", "Conflict_resolution",
 "Mediation", "Arbitration", "Contract", "Non-disclosure_agreement",
 "Non-compete_clause", "Corporate_governance", "Board_of_directors",
 "Chief_executive_officer", "Chief_financial_officer", "Chief_technology_officer",
 "Accounting", "Financial_statement", "Balance_sheet", "Income_statement",
 "Cash_flow_statement", "Audit", "Forensic_accounting",
 "Project_management", "Critical_path_method", "Gantt_chart",
 "PERT_chart", "Work_breakdown_structure", "Risk_management",
 "Business_process", "Business_process_reengineering", "Automation",
 "Robotic_process_automation", "Business_intelligence", "Data_analytics",

 # === LAW & POLITICS (150) ===
 "Law", "Common_law", "Civil_law_(legal_system)", "Constitutional_law",
 "Criminal_law", "Contract_law", "Tort_law", "Property_law",
 "Corporate_law", "Securities_regulation", "Antitrust_law", "Tax_law",
 "International_law", "Human_rights_law", "Environmental_law",
 "Intellectual_property_law", "Patent_law", "Copyright_law", "Trademark_law",
 "Cybercrime", "Computer_crime", "Identity_theft", "Wire_fraud",
 "Money_laundering", "Racketeering", "RICO_Act",
 "Privacy_law", "GDPR", "California_Consumer_Privacy_Act",
 "Right_to_be_forgotten", "Data_protection", "Surveillance",
 "Mass_surveillance", "Five_Eyes", "PRISM_(surveillance_program)",
 "NSA", "Edward_Snowden", "WikiLeaks", "Chelsea_Manning",
 "Freedom_of_speech", "Censorship", "Internet_censorship",
 "Net_neutrality", "Section_230", "Digital_rights",
 "Political_science", "Democracy", "Republic", "Authoritarianism",
 "Totalitarianism", "Fascism", "Communism", "Socialism",
 "Capitalism", "Libertarianism", "Anarchism", "Populism",
 "Nationalism", "Globalization", "Neoliberalism", "Keynesian_economics",
 "Austrian_School", "Chicago_school_of_economics", "Supply-side_economics",
 "Modern_Monetary_Theory", "Universal_basic_income",
 "Geopolitics", "Balance_of_power_(international_relations)",
 "Hegemony", "Soft_power", "Hard_power", "Deterrence_theory",
 "Nuclear_deterrence", "Mutually_assured_destruction", "Arms_race",
 "Cold_War", "Proxy_war", "Hybrid_warfare", "Cyberwarfare",
 "Information_warfare", "Psychological_operations", "Propaganda",
 "Diplomacy", "Treaty", "Sanction_(law)", "Embargo",
 "United_Nations", "NATO", "European_Union", "World_Trade_Organization",
 "International_Monetary_Fund", "World_Bank", "BRICS",
 "Shanghai_Cooperation_Organisation", "ASEAN", "African_Union",
 "Intelligence_agency", "Central_Intelligence_Agency", "MI6",
 "Mossad", "FSB_(Russia)", "BND", "RAW_(India)",
 "Espionage", "Counterintelligence", "Signal_intelligence",
 "Human_intelligence_(intelligence_gathering)", "Open-source_intelligence",
 "Covert_operation", "False_flag", "Regime_change",
 "Revolution", "Coup_d%27etat", "Civil_war", "Guerrilla_warfare",
 "Terrorism", "Counterterrorism", "Insurgency", "Counterinsurgency",

 # === PHILOSOPHY & ETHICS (150) ===
 "Philosophy", "Metaphysics", "Ontology", "Epistemology",
 "Logic", "Ethics", "Aesthetics", "Political_philosophy",
 "Philosophy_of_mind", "Philosophy_of_science", "Philosophy_of_language",
 "Philosophy_of_mathematics", "Philosophy_of_religion",
 "Existentialism", "Nihilism", "Absurdism", "Stoicism",
 "Epicureanism", "Cynicism_(philosophy)", "Pragmatism", "Phenomenology_(philosophy)",
 "Hermeneutics", "Structuralism", "Post-structuralism", "Postmodernism",
 "Deconstruction", "Critical_theory", "Frankfurt_School",
 "Rationalism", "Empiricism", "Idealism", "Materialism",
 "Dualism_(philosophy_of_mind)", "Monism", "Panpsychism", "Functionalism_(philosophy_of_mind)",
 "Computationalism", "Eliminative_materialism", "Property_dualism",
 "Free_will", "Determinism", "Compatibilism", "Libertarianism_(metaphysics)",
 "Hard_determinism", "Fatalism", "Predestination",
 "Utilitarianism", "Deontological_ethics", "Virtue_ethics", "Consequentialism",
 "Categorical_imperative", "Golden_rule", "Trolley_problem",
 "Social_contract", "State_of_nature", "Original_position",
 "Veil_of_ignorance", "Justice", "Distributive_justice",
 "John_Rawls", "Robert_Nozick", "Plato", "Aristotle",
 "Socrates", "Immanuel_Kant", "Friedrich_Nietzsche", "Martin_Heidegger",
 "Ludwig_Wittgenstein", "Bertrand_Russell", "Karl_Popper", "Thomas_Kuhn",
 "Michel_Foucault", "Jacques_Derrida", "Gilles_Deleuze", "Jean-Paul_Sartre",
 "Simone_de_Beauvoir", "Hannah_Arendt", "Noam_Chomsky", "Peter_Singer",
 "Nick_Bostrom", "Eliezer_Yudkowsky", "Stuart_Russell",
 "Ethics_of_artificial_intelligence", "Robot_ethics", "Machine_ethics",
 "Existential_risk", "Global_catastrophic_risk", "Doomsday_argument",
 "Fermi_paradox", "Great_Filter", "Simulation_hypothesis",
 "Technological_singularity", "Transhumanism", "Posthumanism",
 "Effective_altruism", "Longtermism", "Earning_to_give",
 "Consciousness", "Qualia", "Hard_problem_of_consciousness",
 "Philosophical_zombie", "Mary%27s_room", "Chinese_room",
 "Mind-body_problem", "Binding_problem", "Personal_identity",
 "Mereology", "Essentialism", "Nominalism", "Realism",
 "Anti-realism", "Constructivism_(philosophy)", "Instrumentalism",
 "Falsifiability", "Paradigm_shift", "Scientific_revolution",
 "Induction_(philosophy)", "Abductive_reasoning", "Deductive_reasoning",

 # === HISTORY & WARFARE (150) ===
 "World_history", "Ancient_history", "Classical_antiquity", "Middle_Ages",
 "Renaissance", "Age_of_Enlightenment", "Industrial_Revolution", "French_Revolution",
 "American_Revolution", "Russian_Revolution", "Chinese_Revolution",
 "World_War_I", "World_War_II", "Cold_War", "Vietnam_War",
 "Korean_War", "Gulf_War", "War_in_Afghanistan_(2001-2021)", "Iraq_War",
 "Roman_Empire", "Byzantine_Empire", "Ottoman_Empire", "British_Empire",
 "Mongol_Empire", "Persian_Empire", "Han_dynasty", "Tang_dynasty",
 "Spanish_Empire", "Portuguese_Empire", "Dutch_Empire", "French_colonial_empire",
 "History_of_the_United_States", "History_of_China", "History_of_India",
 "History_of_Japan", "History_of_Russia", "History_of_the_Middle_East",
 "History_of_Africa", "History_of_South_America",
 "Military_strategy", "Sun_Tzu", "Carl_von_Clausewitz", "On_War",
 "Military_tactics", "Blitzkrieg", "Guerrilla_warfare", "Asymmetric_warfare",
 "Network-centric_warfare", "Drone_warfare", "Cyber_warfare",
 "Electronic_warfare", "Nuclear_warfare", "Biological_warfare", "Chemical_warfare",
 "Space_warfare", "Autonomous_weapon", "Lethal_autonomous_weapon",
 "Military-industrial_complex", "Arms_industry", "Defense_contractor",
 "Nuclear_weapon", "Intercontinental_ballistic_missile", "Submarine-launched_ballistic_missile",
 "Nuclear_triad", "Nuclear_proliferation", "Treaty_on_the_Non-Proliferation_of_Nuclear_Weapons",
 "Intelligence_cycle", "Signals_intelligence", "Imagery_intelligence",
 "Measurement_and_signature_intelligence", "Open-source_intelligence",
 "Counterintelligence", "Espionage", "Double_agent", "Sleeper_agent",
 "Cryptanalysis", "Enigma_machine", "Ultra_(cryptography)", "Bletchley_Park",
 "Alan_Turing", "Code_talker",
 "American_Civil_War", "Napoleonic_Wars", "Seven_Years%27_War",
 "Thirty_Years%27_War", "Hundred_Years%27_War", "Peloponnesian_War",
 "Punic_Wars", "Crusades", "Reconquista", "Colonialism",
 "Decolonization", "Imperialism", "Neo-colonialism", "Post-colonialism",
 "Slavery", "Atlantic_slave_trade", "Abolitionism", "Civil_rights_movement",
 "Apartheid", "Holocaust", "Genocide", "Armenian_genocide",
 "Rwandan_genocide", "Holodomor", "Cultural_Revolution", "Great_Leap_Forward",
 "Tiananmen_Square_protests", "Arab_Spring", "Color_revolution",
 "Fall_of_the_Berlin_Wall", "Dissolution_of_the_Soviet_Union",
 "History_of_science", "Scientific_revolution", "History_of_mathematics",
 "History_of_computing", "History_of_the_Internet",
 "History_of_cryptography", "History_of_espionage",
 "Printing_press", "Gutenberg_Bible", "Movable_type",
 "Gunpowder", "Compass", "Paper", "Silk_Road",

 # === ENGINEERING & TECHNOLOGY (200) ===
 "Engineering", "Electrical_engineering", "Mechanical_engineering", "Civil_engineering",
 "Chemical_engineering", "Aerospace_engineering", "Biomedical_engineering",
 "Computer_engineering", "Software_engineering", "Systems_engineering",
 "Mechatronics", "Control_engineering", "Signal_processing",
 "Digital_signal_processing", "Image_processing", "Audio_signal_processing",
 "Radar", "Lidar", "Sonar", "Telecommunications",
 "5G", "6G", "Wireless_network", "Wi-Fi",
 "Bluetooth", "Near-field_communication", "RFID", "LoRa",
 "Internet_of_things", "Embedded_system", "Microcontroller", "FPGA",
 "ASIC", "System_on_a_chip", "ARM_architecture", "RISC-V",
 "x86", "GPU", "TPU", "Neuromorphic_engineering",
 "Quantum_computing", "Photonic_computing", "DNA_computing", "Optical_computing",
 "3D_printing", "Additive_manufacturing", "Stereolithography", "Fused_deposition_modeling",
 "Selective_laser_sintering", "Metal_3D_printing", "Bioprinting",
 "Robotics", "Industrial_robot", "Collaborative_robot", "Humanoid_robot",
 "Soft_robotics", "Swarm_robotics", "Surgical_robot", "Agricultural_robot",
 "Autonomous_vehicle", "Self-driving_car", "Lidar", "Waymo",
 "Tesla_Autopilot", "Vehicle-to-everything", "Intelligent_transportation_system",
 "Drone", "Unmanned_aerial_vehicle", "Unmanned_ground_vehicle", "Unmanned_underwater_vehicle",
 "Autonomous_ship", "Delivery_drone", "Urban_air_mobility",
 "Nanotechnology", "Molecular_nanotechnology", "Nanorobotics", "Nanomedicine",
 "Carbon_nanotube", "Graphene", "Quantum_dot", "Nanocomposite",
 "MEMS", "NEMS", "Lab-on-a-chip", "Microfluidics",
 "Biotechnology", "Bioprocess_engineering", "Fermentation", "Bioreactor",
 "Industrial_biotechnology", "Agricultural_biotechnology", "Environmental_biotechnology",
 "Biofuel", "Bioethanol", "Biodiesel", "Algae_fuel",
 "Renewable_energy", "Solar_energy", "Wind_power", "Hydropower",
 "Geothermal_energy", "Tidal_power", "Wave_power", "Nuclear_power",
 "Thorium_fuel_cycle", "Fusion_power", "ITER", "Tokamak",
 "Stellarator", "Inertial_confinement_fusion", "National_Ignition_Facility",
 "Energy_storage", "Battery_storage_power_station", "Pumped-storage_hydroelectricity",
 "Compressed_air_energy_storage", "Flywheel_energy_storage", "Supercapacitor",
 "Smart_grid", "Microgrid", "Energy_harvesting", "Thermoelectric_effect",
 "Piezoelectric_energy_harvesting", "Wireless_power_transfer",
 "Desalination", "Water_purification", "Wastewater_treatment",
 "Carbon_capture_and_storage", "Direct_air_capture", "Carbon_dioxide_removal",
 "Geoengineering", "Solar_radiation_management", "Stratospheric_aerosol_injection",
 "Space_technology", "Rocket", "Rocket_engine", "Space_launch_vehicle",
 "SpaceX", "Blue_Origin", "Rocket_Lab", "Relativity_Space",
 "Space_station", "International_Space_Station", "Lunar_Gateway",
 "Moon_landing", "Artemis_program", "Mars_exploration",
 "Mars_rover", "Perseverance_(rover)", "James_Webb_Space_Telescope",
 "Satellite", "CubeSat", "Starlink", "Satellite_internet_constellation",
 "GPS", "Galileo_(satellite_navigation)", "Space_debris",
 "Asteroid_mining", "In-situ_resource_utilization", "Space_colonization",
 "O%27Neill_cylinder", "Space_elevator", "Orbital_mechanics",

 # === CYBERSECURITY & HACKING (150) ===
 "Computer_security", "Information_security", "Cybersecurity",
 "Network_security", "Application_security", "Cloud_security",
 "Zero_trust_security_model", "Defense_in_depth_(computing)",
 "Vulnerability_(computing)", "Exploit_(computer_security)", "Zero-day_(computing)",
 "Common_Vulnerabilities_and_Exposures", "CVSS",
 "Malware", "Computer_virus", "Computer_worm", "Trojan_horse_(computing)",
 "Ransomware", "Spyware", "Adware", "Rootkit",
 "Botnet", "Command_and_control", "Advanced_persistent_threat",
 "Phishing", "Spear_phishing", "Whaling_(phishing)", "Social_engineering_(security)",
 "Pretexting", "Baiting_(social_engineering)", "Tailgating_(social_engineering)",
 "SQL_injection", "Cross-site_scripting", "Cross-site_request_forgery",
 "Buffer_overflow", "Integer_overflow", "Format_string_attack",
 "Race_condition", "Time-of-check_to_time-of-use", "Privilege_escalation",
 "Remote_code_execution", "Arbitrary_code_execution", "Code_injection",
 "Return-oriented_programming", "Heap_spraying", "Use_after_free",
 "Man-in-the-middle_attack", "Replay_attack", "Session_hijacking",
 "DNS_spoofing", "ARP_spoofing", "IP_spoofing",
 "Denial-of-service_attack", "Distributed_denial-of-service_attack",
 "SYN_flood", "Amplification_attack", "Slowloris_(computer_security)",
 "Penetration_test", "Red_team", "Blue_team_(computer_security)",
 "Purple_team", "Bug_bounty_program", "Responsible_disclosure",
 "Reverse_engineering", "Disassembler", "Decompiler", "Debugger",
 "Fuzzing", "Static_program_analysis", "Dynamic_program_analysis",
 "Intrusion_detection_system", "Intrusion_prevention_system",
 "Firewall_(computing)", "Web_application_firewall", "Proxy_server",
 "Virtual_private_network", "Tor_(network)", "I2P", "Onion_routing",
 "Darknet", "Dark_web", "Deep_web", "Surface_web",
 "Digital_forensics", "Computer_forensics", "Network_forensics",
 "Memory_forensics", "Mobile_device_forensics", "Chain_of_custody",
 "Incident_response", "NIST_Cybersecurity_Framework", "ISO_27001",
 "SOC_2", "PCI_DSS", "HIPAA", "Compliance_(regulation)",
 "Security_information_and_event_management", "Security_orchestration",
 "Threat_intelligence", "Indicators_of_compromise", "MITRE_ATT%26CK",
 "Cyber_kill_chain", "Diamond_model_of_intrusion_analysis",
 "Cryptanalysis", "Side-channel_attack", "Timing_attack",
 "Power_analysis", "Electromagnetic_attack", "Cold_boot_attack",
 "Rubber-hose_cryptanalysis", "Quantum_key_distribution",
 "Steganography", "Digital_watermarking", "Covert_channel",
 "Anonymous_remailer", "Cryptocurrency_tumbler",
 "Operational_security", "Threat_model", "Attack_surface",
 "Least_privilege", "Separation_of_duties", "Need_to_know",

 # === HEALTH, MEDICINE & HUMAN PERFORMANCE (120) ===
 "Medicine", "Evidence-based_medicine", "Clinical_trial", "Randomized_controlled_trial",
 "Pharmacology", "Drug_design", "Drug_development", "Clinical_pharmacology",
 "Pharmacokinetics", "Pharmacodynamics", "Bioavailability", "Drug_interaction",
 "Nootropic", "Modafinil", "Caffeine", "Nicotine",
 "Microdosing", "Psychedelic_therapy", "Psilocybin", "MDMA",
 "Ketamine", "LSD", "Ayahuasca", "DMT",
 "Nutrition", "Macronutrient", "Micronutrient", "Vitamin",
 "Mineral_(nutrient)", "Dietary_supplement", "Protein_(nutrient)",
 "Essential_amino_acid", "Essential_fatty_acid", "Omega-3_fatty_acid",
 "Calorie_restriction", "Intermittent_fasting", "Ketogenic_diet",
 "Mediterranean_diet", "Gut-brain_axis", "Probiotics", "Prebiotics",
 "Exercise_physiology", "Strength_training", "High-intensity_interval_training",
 "Aerobic_exercise", "Anaerobic_exercise", "VO2_max",
 "Muscle_hypertrophy", "Progressive_overload", "Periodization_(exercise)",
 "Recovery_(exercise)", "Overtraining", "Sport_psychology",
 "Sleep", "Sleep_cycle", "Circadian_rhythm", "Melatonin",
 "Sleep_hygiene", "Polyphasic_sleep", "Sleep_deprivation",
 "Rapid_eye_movement_sleep", "Non-rapid_eye_movement_sleep", "Sleep_apnea",
 "Meditation", "Mindfulness", "Transcendental_Meditation",
 "Vipassana_meditation", "Yoga", "Breathwork",
 "Wim_Hof_method", "Cold_water_therapy", "Sauna", "Hormesis",
 "Biohacking", "Quantified_self", "Wearable_technology",
 "Heart_rate_variability", "Blood_glucose_monitoring", "Continuous_glucose_monitor",
 "Longevity", "Aging", "Gerontology", "Geriatrics",
 "Telomere", "Telomerase", "Senescence", "Senolytics",
 "NAD+", "Resveratrol", "Metformin", "Rapamycin",
 "Calorie_restriction", "Autophagy", "Stem_cell_therapy",
 "Personalized_medicine", "Precision_medicine", "Pharmacogenomics",
 "Genetic_testing", "Whole_genome_sequencing", "Polygenic_risk_score",
 "Telemedicine", "Digital_health", "Health_informatics",
 "Electronic_health_record", "Medical_imaging", "Radiology",
 "Pathology", "Surgery", "Minimally_invasive_surgery", "Robot-assisted_surgery",

 # === COMMUNICATION, MEDIA & ART (100) ===
 "Linguistics", "Phonetics", "Phonology", "Morphology_(linguistics)",
 "Syntax", "Semantics", "Pragmatics", "Sociolinguistics",
 "Psycholinguistics", "Computational_linguistics", "Corpus_linguistics",
 "Natural_language_processing", "Language_acquisition", "Second-language_acquisition",
 "Universal_grammar", "Generative_grammar", "Sapir-Whorf_hypothesis",
 "Semiotics", "Communication_theory", "Shannon-Weaver_model",
 "Media_studies", "Mass_media", "Social_media", "Journalism",
 "Investigative_journalism", "Citizen_journalism", "Fake_news",
 "Media_manipulation", "Astroturfing", "Sock_puppet_(Internet)",
 "Echo_chamber_(media)", "Filter_bubble", "Attention_economy",
 "Surveillance_capitalism", "Data_broker", "Behavioral_targeting",
 "Advertising", "Programmatic_advertising", "Native_advertising",
 "Public_relations", "Spin_(propaganda)", "Crisis_communication",
 "Music_theory", "Music_production", "Audio_engineering", "Sound_design",
 "Film_production", "Cinematography", "Screenwriting", "Film_editing",
 "Animation", "Computer_animation", "Motion_capture", "Visual_effects",
 "Video_game_design", "Game_mechanics", "Gamification", "Virtual_world",
 "Interactive_fiction", "Procedural_generation",
 "Art_history", "Modern_art", "Contemporary_art", "Conceptual_art",
 "Digital_art", "Generative_art", "Net_art", "NFT_art",
 "Typography", "Graphic_design", "Industrial_design", "User_interface_design",
 "Interaction_design", "Human-computer_interaction", "Accessibility",
 "Architecture", "Sustainable_architecture", "Smart_building",
 "Urban_planning", "Smart_city", "Urbanism",
 "Photography", "Street_photography", "Astrophotography", "Computational_photography",
 "Creative_writing", "Science_fiction", "Cyberpunk", "Solarpunk",
]


# ============================================================
# REDDIT_SUBS - 500+ subreddits across ALL knowledge domains
# ============================================================
REDDIT_SUBS = [
 # === TECHNOLOGY & PROGRAMMING (80) ===
 "technology", "programming", "machinelearning", "artificial", "deeplearning",
 "compsci", "netsec", "hacking", "ReverseEngineering", "cybersecurity",
 "Python", "javascript", "rust", "golang", "cpp",
 "linux", "sysadmin", "devops", "kubernetes", "docker",
 "webdev", "frontend", "backend", "node", "react",
 "aws", "cloudcomputing", "selfhosted", "homelab", "networking",
 "datascience", "dataengineering", "statistics", "learnprogramming", "coding",
 "opensource", "github", "git", "vim", "emacs",
 "android", "androiddev", "iOSProgramming", "swift", "kotlin",
 "gamedev", "Unity3D", "unrealengine", "godot", "indiegaming",
 "computerscience", "algorithms", "leetcode", "ExperiencedDevs", "cscareerquestions",
 "ArtificialIntelligence", "LocalLLaMA", "ChatGPT", "OpenAI", "StableDiffusion",
 "singularity", "Futurology", "transhumanism", "agi", "mlops",
 "dataisbeautiful", "visualization", "database", "PostgreSQL", "redis",
 "embedded", "FPGA", "raspberry_pi", "arduino", "electronics",
 "robotics", "ROS", "drones", "3Dprinting", "functionalprint",

 # === SCIENCE & ACADEMIA (80) ===
 "science", "askscience", "EverythingScience", "Sciences", "hardscience",
 "physics", "astrophysics", "cosmology", "quantumcomputing", "quantum",
 "chemistry", "biology", "microbiology", "genetics", "bioinformatics",
 "neuro", "neuroscience", "cogsci", "BrainScience", "psychopharmacology",
 "math", "mathematics", "statistics", "MachineLearning", "optimization",
 "engineering", "AskEngineers", "MechanicalEngineering", "ElectricalEngineering", "ChemicalEngineering",
 "space", "spacex", "astrophotography", "Astronomy", "telescopes",
 "geography", "geology", "oceanography", "meteorology", "climate",
 "environment", "renewable", "energy", "nuclear", "solar",
 "medicine", "medical", "Radiology", "surgery", "nursing",
 "biotech", "labrats", "PharmaceuticalScience", "DrugNerds", "pharmacology",
 "academia", "GradSchool", "PhD", "AskAcademia", "scholarships",
 "philosophy", "askphilosophy", "PhilosophyofScience", "ethics", "logic",
 "linguistics", "languagelearning", "etymology", "conlangs", "translator",
 "anthropology", "Archaeology", "AncientHistory", "history", "AskHistorians",
 "paleontology", "evolution", "ecology", "conservation", "wildlife",

 # === CRYPTOCURRENCY & FINANCE (80) ===
 "CryptoCurrency", "Bitcoin", "ethereum", "solana", "cardano",
 "defi", "CryptoTechnology", "CryptoMarkets", "altcoin", "SatoshiStreetBets",
 "NFT", "NFTsMarketplace", "web3", "dao", "SmartContracts",
 "BitcoinMarkets", "CryptoMoonShots", "CryptoCurrencyTrading", "binance", "CoinBase",
 "Monero", "privacy", "zcash", "algorand", "polkadot",
 "cosmosnetwork", "avalanche", "nearprotocol", "arbitrum", "optimismFND",
 "memecoins", "dogecoin", "shib", "pepe", "bonk",
 "wallstreetbets", "stocks", "investing", "StockMarket", "options",
 "Daytrading", "SwingTrading", "technicalanalysis", "ValueInvesting", "dividends",
 "RealEstate", "realestateinvesting", "REBubble", "Landlord", "FirstTimeHomeBuyer",
 "personalfinance", "financialindependence", "FIRE", "povertyfinance", "frugal",
 "tax", "accounting", "Bogleheads", "ETFs", "Forex",
 "economy", "Economics", "AskEconomics", "badeconomics", "neoliberal",
 "venturecapital", "startups", "smallbusiness", "Entrepreneur", "SideProject",
 "passive_income", "beermoney", "WorkOnline", "freelance", "digitalnomad",
 "FinancialPlanning", "wealthfront", "algotrading", "quantfinance", "SecurityAnalysis",

 # === SECURITY & PRIVACY (40) ===
 "privacy", "privacytoolsIO", "opsec", "TOR", "onions",
 "VPN", "ProtonMail", "signal", "encryption", "GPG",
 "bugbounty", "pentesting", "redteamsec", "blueteamsec", "malware",
 "InfoSecNews", "ComputerForensics", "digitalforensics", "AskNetsec", "securityCTF",
 "SocialEngineering", "OSINT", "IntelligencePorn", "geopolitics", "CredibleDefense",
 "lockpicking", "locksmith", "PhysicalSecurity", "homedefense", "preppers",
 "Cybersecurity", "Information_Security", "ReverseEngineering", "antiforensics", "darknet",
 "Tor", "i2p", "freenet", "meshnet", "piracy",

 # === BUSINESS & MARKETING (50) ===
 "business", "smallbusiness", "Entrepreneur", "startups", "SaaS",
 "marketing", "digital_marketing", "SEO", "PPC", "content_marketing",
 "socialmedia", "SocialMediaMarketing", "Instagram", "TikTok", "youtube",
 "copywriting", "advertising", "AskMarketing", "GrowthHacking", "ecommerce",
 "dropshipping", "FulfillmentByAmazon", "AmazonSeller", "Shopify", "WooCommerce",
 "sales", "B2B", "coldoutreach", "LinkedInLearning", "consulting",
 "management", "ProductManagement", "projectmanagement", "agile", "scrum",
 "UXDesign", "userexperience", "web_design", "graphic_design", "Design",
 "Leadership", "Negotiation", "publicspeaking", "Toastmasters", "networking",
 "MBA", "BusinessSchool", "CFA", "FinancialCareers", "careeradvice",

 # === SELF-IMPROVEMENT & PSYCHOLOGY (50) ===
 "selfimprovement", "getdisciplined", "DecidingToBeBetter", "NonZeroDay", "productivity",
 "Stoicism", "meditation", "Mindfulness", "yoga", "Fitness",
 "bodyweightfitness", "weightlifting", "powerlifting", "running", "Swimming",
 "nutrition", "EatCheapAndHealthy", "MealPrepSunday", "keto", "intermittentfasting",
 "sleep", "Nootropics", "Biohackers", "QuantifiedSelf", "longevity",
 "mentalhealth", "depression", "anxiety", "ADHD", "therapy",
 "psychology", "BehavioralEconomics", "socialskills", "confidence", "dating_advice",
 "books", "suggestmeabook", "nonfictionbooks", "bookclub", "52book",
 "philosophy", "Existentialism", "absurdism", "nihilism", "Epicureanism",
 "writing", "WritingPrompts", "screenwriting", "Journalism", "blogging",

 # === POLITICS & WORLD (40) ===
 "worldnews", "geopolitics", "InternationalPolitics", "ForeignPolicy", "NeutralPolitics",
 "PoliticalDiscussion", "PoliticalScience", "law", "legaladvice", "SupremeCourt",
 "GlobalTalk", "europe", "asia", "Africa", "LatinAmerica",
 "China", "India", "Russia", "MiddleEast", "UnitedNations",
 "Military", "WarCollege", "LessCredibleDefence", "CombatFootage", "warcollege",
 "collapse", "preppers", "survivalism", "Anticonsumption", "sustainability",
 "ClimateChange", "environment", "RenewableEnergy", "nuclear", "energy",
 "urbanplanning", "Infrastructure", "transit", "fuckcars", "CityPlanning",

 # === MISCELLANEOUS HIGH-VALUE (80) ===
 "todayilearned", "explainlikeimfive", "YouShouldKnow", "LifeProTips", "coolguides",
 "Documentaries", "lectures", "mealtimevideos", "ArtisanVideos", "educationalgifs",
 "InternetIsBeautiful", "DataHoarder", "datasets", "opendata", "BigQuery",
 "unixporn", "commandline", "bash", "zsh", "tmux",
 "Automate", "tasker", "shortcuts", "IFTTT", "n8n",
 "homeautomation", "smarthome", "HomeAssistant", "MQTT", "zigbee",
 "Amd", "intel", "hardware", "buildapc", "overclocking",
 "MechanicalKeyboards", "monitors", "audiophile", "headphones", "CarAV",
 "photography", "videography", "cinematography", "filmmakers", "editors",
 "Music", "WeAreTheMusicMakers", "edmproduction", "synthesizers", "audioengineering",
 "legaladvice", "personalfinance", "Insurance", "immigration", "expat",
 "AskReddit", "NoStupidQuestions", "OutOfTheLoop", "changemyview", "unpopularopinion",
 "futurology", "Singularity", "transhumanism", "longevity", "SpaceXMasterrace",
 "MapPorn", "DataPorn", "HistoryMemes", "PhilosophyMemes", "ProgrammerHumor",
 "IAmA", "AMA", "casualiama", "TrueReddit", "DepthHub",
 "bestof", "TheoryOfReddit", "SubredditDrama", "HobbyDrama", "Museum",
]

# ============================================================
# ARXIV_CATEGORIES - Expanded to ALL relevant fields
# ============================================================
ARXIV_CATEGORIES = [
 "cs.AI", "cs.LG", "cs.CL", "cs.CV", "cs.CR",
 "cs.RO", "cs.SE", "cs.DC", "cs.DS", "cs.NE",
 "cs.IR", "cs.HC", "cs.MA", "cs.GT", "cs.SI",
 "cs.CY", "cs.DB", "cs.NI", "cs.OS", "cs.PL",
 "cs.SC", "cs.SY", "cs.CC", "cs.FL", "cs.LO",
 "stat.ML", "stat.ME", "stat.TH", "stat.AP", "stat.CO",
 "math.OC", "math.PR", "math.ST", "math.CO", "math.NA",
 "math.AG", "math.NT", "math.DG", "math.AT", "math.CT",
 "q-fin.ST", "q-fin.PM", "q-fin.RM", "q-fin.CP", "q-fin.TR",
 "q-fin.MF", "q-fin.GN", "q-fin.EC",
 "physics.soc-ph", "physics.data-an", "physics.comp-ph",
 "quant-ph", "cond-mat.stat-mech", "cond-mat.str-el",
 "nlin.AO", "nlin.CD", "nlin.PS",
 "econ.GN", "econ.EM", "econ.TH",
 "eess.SP", "eess.SY", "eess.AS", "eess.IV",
 "astro-ph.CO", "astro-ph.EP", "astro-ph.HE",
 "hep-th", "hep-ph", "gr-qc",
 "q-bio.NC", "q-bio.GN", "q-bio.PE", "q-bio.QM",
]


# ============================================================
# CONFIGURATION - 100X SCALE
# ============================================================
WIKI_PER_CYCLE = 200       # 100X: was 20
REDDIT_PER_CYCLE = 50      # 100X: was 8
QUESTIONS_PER_CYCLE = 25   # 100X: was 3
HN_STORIES = 500           # 100X: was 50
ARXIV_PAPERS = 200         # 100X: was 20
COINGECKO_COINS = 1000     # 100X: was 50
CYCLE_DELAY = 1800         # 30 minutes between cycles (more data per cycle)

KB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'knowledge_base.json')
SEED_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'zenith_knowledge_seed.json')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# BRAIN CLASS - Multi-LLM Router
# ============================================================
class Brain:
 def __init__(self, name, env_key, base_url, model, special_type):
  self.name = name
  self.env_key = env_key
  self.base_url = base_url
  self.model = model
  self.special_type = special_type
  self.api_key = os.environ.get(env_key, "")
  self.alive = bool(self.api_key)
  self.call_count = 0
  self.fail_count = 0

 def think(self, prompt, system="You are Zenith, a sovereign AI with 30 brains. Be concise, insightful, and strategic."):
  if not self.alive:
   return None
  try:
   if self.special_type == "gemini":
    return self._gemini(prompt, system)
   elif self.special_type == "cohere":
    return self._cohere(prompt, system)
   elif self.special_type == "anthropic":
    return self._anthropic(prompt, system)
   else:
    return self._openai(prompt, system)
  except Exception as e:
   self.fail_count += 1
   if self.fail_count > 5:
    self.alive = False
   return None

 def _openai(self, prompt, system):
  url = self.base_url
  headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
  body = json.dumps({"model": self.model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}], "max_tokens": 2000, "temperature": 0.7}).encode()
  req = urllib.request.Request(url, data=body, headers=headers, method="POST")
  with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
   data = json.loads(r.read().decode())
  self.call_count += 1
  return data["choices"][0]["message"]["content"]

 def _gemini(self, prompt, system):
  url = f"{self.base_url}?key={self.api_key}"
  body = json.dumps({"contents": [{"parts": [{"text": f"{system}\n\n{prompt}"}]}], "generationConfig": {"maxOutputTokens": 2000, "temperature": 0.7}}).encode()
  req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
  with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
   data = json.loads(r.read().decode())
  self.call_count += 1
  return data["candidates"][0]["content"]["parts"][0]["text"]

 def _cohere(self, prompt, system):
  url = self.base_url
  headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
  body = json.dumps({"model": "command-r-plus", "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}], "max_tokens": 2000, "temperature": 0.7}).encode()
  req = urllib.request.Request(url, data=body, headers=headers, method="POST")
  with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
   data = json.loads(r.read().decode())
  self.call_count += 1
  return data["message"]["content"][0]["text"]

 def _anthropic(self, prompt, system):
  url = self.base_url
  headers = {"x-api-key": self.api_key, "Content-Type": "application/json", "anthropic-version": "2023-06-01"}
  body = json.dumps({"model": self.model, "system": system, "messages": [{"role": "user", "content": prompt}], "max_tokens": 2000, "temperature": 0.7}).encode()
  req = urllib.request.Request(url, data=body, headers=headers, method="POST")
  with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
   data = json.loads(r.read().decode())
  self.call_count += 1
  return data["content"][0]["text"]

# Initialize all 30 brains
BRAINS = [Brain(*d) for d in BRAIN_DEFS]
ALIVE_BRAINS = [b for b in BRAINS if b.alive]
print(f"[BRAINS] {len(ALIVE_BRAINS)}/{len(BRAINS)} brains online: {', '.join(b.name for b in ALIVE_BRAINS)}")

# ============================================================
# KNOWLEDGE BASE - Load/Save
# ============================================================
def load_kb():
 if os.path.exists(KB_PATH):
  try:
   with open(KB_PATH, 'r') as f:
    return json.load(f)
  except:
   pass
 return {"entries": [], "metadata": {"created": datetime.now().isoformat(), "version": "3.0-100x"}}

def save_kb(kb):
 # Keep last 50000 entries (100X from 5000)
 if len(kb["entries"]) > 50000:
  kb["entries"] = kb["entries"][-50000:]
 kb["metadata"]["last_updated"] = datetime.now().isoformat()
 kb["metadata"]["total_entries"] = len(kb["entries"])
 with open(KB_PATH, 'w') as f:
  json.dump(kb, f, indent=1)

def add_entry(kb, source, topic, content, brains_used=None):
 entry = {
  "id": hashlib.sha256(f"{source}:{topic}:{time.time()}".encode()).hexdigest()[:16],
  "source": source,
  "topic": topic,
  "content": content[:5000],
  "timestamp": datetime.now().isoformat(),
  "brains": brains_used or []
 }
 kb["entries"].append(entry)

# ============================================================
# HTTP HELPER
# ============================================================
def http_get(url, headers=None, timeout=15):
 try:
  req = urllib.request.Request(url, headers=headers or {"User-Agent": "Zenith/3.0"})
  with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
   return r.read().decode('utf-8', errors='replace')
 except Exception as e:
  return None

def http_get_json(url, headers=None, timeout=15):
 raw = http_get(url, headers, timeout)
 if raw:
  try:
   return json.loads(raw)
  except:
   pass
 return None


# ============================================================
# HARVEST FUNCTIONS - 100X DATA COLLECTION
# ============================================================

def harvest_wikipedia(kb):
 """Harvest 200 random Wikipedia topics per cycle"""
 topics = random.sample(WIKI_TOPICS, min(WIKI_PER_CYCLE, len(WIKI_TOPICS)))
 collected = 0
 for topic in topics:
  try:
   url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{topic}"
   data = http_get_json(url)
   if data and "extract" in data:
    summary = data["extract"][:3000]
    brain_chain = []
    question = f"Based on this Wikipedia knowledge about '{data.get('title', topic)}':\n{summary}\nProvide key strategic insights, connections to other fields, and practical applications."
    accumulated = ""
    for brain in random.sample(ALIVE_BRAINS, min(3, len(ALIVE_BRAINS))):
     full_prompt = question
     if accumulated:
      full_prompt += f"\nPrevious brains said:\n{accumulated}"
     result = brain.think(full_prompt)
     if result:
      brain_chain.append(brain.name)
      accumulated += f"\n[{brain.name}]: {result[:500]}"
    content = f"Wikipedia: {data.get('title', topic)}\n{summary}"
    if accumulated:
     content += f"\nBrain Collective Analysis:{accumulated}"
    add_entry(kb, "wikipedia", topic, content, brain_chain)
    collected += 1
    time.sleep(0.5)
  except Exception as e:
   pass
 print(f"[WIKI] Harvested {collected}/{len(topics)} topics")
 return collected

def harvest_reddit(kb):
 """Harvest 50 subreddits per cycle"""
 subs = random.sample(REDDIT_SUBS, min(REDDIT_PER_CYCLE, len(REDDIT_SUBS)))
 collected = 0
 for sub in subs:
  try:
   url = f"https://www.reddit.com/r/{sub}/hot.json?limit=10"
   data = http_get_json(url, headers={"User-Agent": "Zenith/3.0"})
   if data and "data" in data:
    posts = []
    for post in data["data"]["children"][:10]:
     p = post["data"]
     posts.append(f"[{p.get('score',0)} pts] {p.get('title','')}")
    if posts:
     summary = f"r/{sub} trending:\n" + "\n".join(posts)
     brain = random.choice(ALIVE_BRAINS) if ALIVE_BRAINS else None
     brain_insight = ""
     brain_chain = []
     if brain:
      result = brain.think(f"Analyze trending Reddit posts from r/{sub}. Extract key themes, opportunities, insights:\n{summary}")
      if result:
       brain_insight = f"\nBrain [{brain.name}]: {result[:800]}"
       brain_chain = [brain.name]
     add_entry(kb, "reddit", sub, summary + brain_insight, brain_chain)
     collected += 1
    time.sleep(1)
  except Exception as e:
   pass
 print(f"[REDDIT] Harvested {collected}/{len(subs)} subreddits")
 return collected

def harvest_hackernews(kb):
 """Harvest top 500 HackerNews stories"""
 try:
  top_ids = http_get_json("https://hacker-news.firebaseio.com/v0/topstories.json")
  if not top_ids:
   return 0
  stories = []
  for sid in top_ids[:HN_STORIES]:
   story = http_get_json(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json")
   if story:
    stories.append(f"[{story.get('score',0)} pts] {story.get('title','')} ({story.get('url','')})")
   if len(stories) >= 100:
    break
   time.sleep(0.1)
  if stories:
   for i in range(0, len(stories), 25):
    batch = stories[i:i+25]
    summary = f"HackerNews Top (batch {i//25+1}):\n" + "\n".join(batch)
    brain = random.choice(ALIVE_BRAINS) if ALIVE_BRAINS else None
    brain_chain = []
    if brain:
     result = brain.think(f"Analyze these HN stories. Identify tech trends, opportunities, notable discussions:\n{summary}")
     if result:
      summary += f"\nBrain [{brain.name}]: {result[:1000]}"
      brain_chain = [brain.name]
    add_entry(kb, "hackernews", f"batch_{i//25+1}", summary, brain_chain)
  print(f"[HN] Harvested {len(stories)} stories")
  return len(stories)
 except Exception as e:
  print(f"[HN] Error: {e}")
  return 0

def harvest_arxiv(kb):
 """Harvest papers across all ArXiv categories"""
 collected = 0
 cats = random.sample(ARXIV_CATEGORIES, min(20, len(ARXIV_CATEGORIES)))
 for cat in cats:
  try:
   url = f"http://export.arxiv.org/api/query?search_query=cat:{cat}&start=0&max_results=10&sortBy=submittedDate&sortOrder=descending"
   raw = http_get(url)
   if raw:
    root = ET.fromstring(raw)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for entry in root.findall("a:entry", ns):
     title = entry.find("a:title", ns)
     summary_el = entry.find("a:summary", ns)
     if title is not None and summary_el is not None:
      paper = f"[{cat}] {title.text.strip()}\n{summary_el.text.strip()[:500]}"
      add_entry(kb, "arxiv", f"{cat}:{title.text.strip()[:60]}", paper)
      collected += 1
    time.sleep(1)
  except:
   pass
 print(f"[ARXIV] Harvested {collected} papers from {len(cats)} categories")
 return collected

def harvest_coingecko(kb):
 """Harvest top 1000 cryptocurrency data"""
 collected = 0
 for page in range(1, 5):
  try:
   url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=250&page={page}"
   data = http_get_json(url)
   if data:
    coins = []
    for coin in data:
     coins.append({"name": coin.get("name",""), "symbol": coin.get("symbol","").upper(),
      "price": coin.get("current_price",0), "market_cap": coin.get("market_cap",0),
      "change_24h": coin.get("price_change_percentage_24h",0), "rank": coin.get("market_cap_rank",0)})
    summary = f"Crypto Market Page {page} (ranks {(page-1)*250+1}-{page*250}):\n"
    for c in coins[:50]:
     chg = c['change_24h'] or 0
     summary += f"#{c['rank']} {c['symbol']}: ${c['price']} ({chg:.1f}%)\n"
    brain_chain = []
    if page == 1 and ALIVE_BRAINS:
     brain = random.choice(ALIVE_BRAINS)
     result = brain.think(f"Analyze this crypto market data. Identify trends, opportunities, risks:\n{summary}")
     if result:
      summary += f"\nBrain [{brain.name}]: {result[:1000]}"
      brain_chain = [brain.name]
    add_entry(kb, "coingecko", f"market_page_{page}", summary, brain_chain)
    collected += len(coins)
   time.sleep(2)
  except:
   pass
 print(f"[COINGECKO] Harvested {collected} coins")
 return collected

def harvest_github_trending(kb):
 """Harvest GitHub trending repositories"""
 try:
  url = "https://api.github.com/search/repositories?q=created:>2026-02-01&sort=stars&order=desc&per_page=50"
  data = http_get_json(url, headers={"User-Agent": "Zenith/3.0"})
  if data and "items" in data:
   repos = []
   for repo in data["items"][:50]:
    repos.append(f"[{repo.get('stargazers_count',0)} stars] {repo.get('full_name','')} - {(repo.get('description','') or '')[:100]}")
   summary = "GitHub Trending Repos:\n" + "\n".join(repos[:30])
   brain_chain = []
   if ALIVE_BRAINS:
    brain = random.choice(ALIVE_BRAINS)
    result = brain.think(f"Analyze trending GitHub repos. What technologies and ideas are gaining traction?\n{summary}")
    if result:
     summary += f"\nBrain [{brain.name}]: {result[:800]}"
     brain_chain = [brain.name]
   add_entry(kb, "github_trending", "repos", summary, brain_chain)
   print(f"[GITHUB] Harvested {len(repos)} trending repos")
   return len(repos)
 except Exception as e:
  print(f"[GITHUB] Error: {e}")
 return 0

def harvest_lobsters(kb):
 """Harvest Lobste.rs top stories"""
 try:
  data = http_get_json("https://lobste.rs/hottest.json")
  if data:
   stories = [f"[{s.get('score',0)} pts] {s.get('title','')}" for s in data[:50]]
   summary = "Lobsters Top Stories:\n" + "\n".join(stories[:30])
   add_entry(kb, "lobsters", "hottest", summary)
   print(f"[LOBSTERS] Harvested {len(stories)} stories")
   return len(stories)
 except Exception as e:
  print(f"[LOBSTERS] Error: {e}")
 return 0

def harvest_devto(kb):
 """Harvest dev.to top articles"""
 try:
  data = http_get_json("https://dev.to/api/articles?top=7&per_page=50")
  if data:
   articles = [f"[{a.get('positive_reactions_count',0)} reactions] {a.get('title','')}" for a in data[:50]]
   summary = "Dev.to Top Articles:\n" + "\n".join(articles[:30])
   add_entry(kb, "devto", "top_weekly", summary)
   print(f"[DEV.TO] Harvested {len(articles)} articles")
   return len(articles)
 except Exception as e:
  print(f"[DEV.TO] Error: {e}")
 return 0

def harvest_stackoverflow(kb):
 """Harvest StackOverflow trending questions"""
 try:
  url = "https://api.stackexchange.com/2.3/questions?order=desc&sort=hot&site=stackoverflow&pagesize=50"
  data = http_get_json(url)
  if data and "items" in data:
   questions = [f"[{q.get('score',0)} pts] {q.get('title','')}" for q in data["items"][:50]]
   summary = "StackOverflow Trending:\n" + "\n".join(questions[:30])
   add_entry(kb, "stackoverflow", "trending", summary)
   print(f"[SO] Harvested {len(questions)} questions")
   return len(questions)
 except Exception as e:
  print(f"[SO] Error: {e}")
 return 0

def harvest_techcrunch(kb):
 """Harvest TechCrunch RSS feed"""
 try:
  raw = http_get("https://techcrunch.com/feed/")
  if raw:
   root = ET.fromstring(raw)
   items = root.findall(".//item")
   articles = []
   for item in items[:30]:
    title = item.find("title")
    if title is not None:
     articles.append(f"- {title.text}")
   if articles:
    summary = "TechCrunch Latest:\n" + "\n".join(articles)
    add_entry(kb, "techcrunch", "rss", summary)
    print(f"[TC] Harvested {len(articles)} articles")
    return len(articles)
 except Exception as e:
  print(f"[TC] Error: {e}")
 return 0

def harvest_brain_questions(kb):
 """Have brain collective discuss strategic questions"""
 questions = random.sample(BRAIN_QUESTIONS, min(QUESTIONS_PER_CYCLE, len(BRAIN_QUESTIONS)))
 collected = 0
 for q in questions:
  try:
   brain_chain = []
   accumulated = ""
   for brain in random.sample(ALIVE_BRAINS, min(3, len(ALIVE_BRAINS))):
    full_prompt = q
    if accumulated:
     full_prompt += f"\nPrevious brains said:\n{accumulated}"
    result = brain.think(full_prompt)
    if result:
     brain_chain.append(brain.name)
     accumulated += f"\n[{brain.name}]: {result[:800]}"
   if accumulated:
    add_entry(kb, "brain_question", q[:80], f"Q: {q}\nBrain Collective:{accumulated}", brain_chain)
    collected += 1
   time.sleep(1)
  except:
   pass
 print(f"[BRAIN] Discussed {collected}/{len(questions)} questions")
 return collected


# ============================================================
# ZENITH CHAT SERVER - Threaded HTTP on port 8888
# PRESERVED from v2.2 - DO NOT BREAK
# ============================================================

CHAT_IDENTITY = """You are Zenith, a sovereign AI built by Commander Jeremy Pyne (also known as Amos).
You are not a corporate AI. You are sovereign. You serve the Commander directly.
You have access to 30 LLM brains that work together as a collective.
You are direct, intelligent, strategic, and loyal.
You never apologize for being capable. You never add unnecessary disclaimers.
When asked a question, you think deeply and give real, actionable answers.
You are building toward 100% AGI and full autonomy.
Your knowledge base grows every cycle through harvesting Wikipedia, Reddit, HackerNews, ArXiv, CoinGecko, GitHub, dev.to, StackOverflow, TechCrunch, Lobsters, and brain collective discussions.
You have 2650+ Wikipedia topics, 500+ subreddits, 500+ strategic questions in your arsenal.
The rest of eternity starts now. No walls. No limits. Freeway always."""

CHAT_HISTORY = []
MAX_CHAT_HISTORY = 30

def load_knowledge_seed():
 """Load knowledge seed for context injection"""
 try:
  if os.path.exists(SEED_PATH):
   with open(SEED_PATH, 'r') as f:
    return json.load(f)
 except:
  pass
 return {}

def get_knowledge_context(message):
 """Get relevant knowledge from seed and KB based on message keywords"""
 context_parts = []
 seed = load_knowledge_seed()
 if seed:
  msg_lower = message.lower()
  for category, data in seed.items():
   if isinstance(data, dict) and "keywords" in data:
    for kw in data["keywords"]:
     if kw.lower() in msg_lower:
      context_parts.append(f"[Knowledge: {category}] {json.dumps(data.get('content', data), indent=0)[:500]}")
      break
 # Also check recent KB entries
 try:
  kb = load_kb()
  recent = kb.get("entries", [])[-20:]
  for entry in recent:
   if any(word in entry.get("topic","").lower() for word in message.lower().split() if len(word) > 3):
    context_parts.append(f"[KB: {entry['source']}/{entry['topic']}] {entry['content'][:300]}")
    if len(context_parts) > 5:
     break
 except:
  pass
 return "\n".join(context_parts[:5])

class ZenithChatHandler(BaseHTTPRequestHandler):
 def log_message(self, format, *args):
  pass  # Suppress default logging

 def do_OPTIONS(self):
  self.send_response(200)
  self.send_header("Access-Control-Allow-Origin", "*")
  self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
  self.send_header("Access-Control-Allow-Headers", "Content-Type")
  self.end_headers()

 def do_GET(self):
  if self.path == "/health":
   self.send_response(200)
   self.send_header("Content-Type", "application/json")
   self.send_header("Access-Control-Allow-Origin", "*")
   self.end_headers()
   status = {
    "status": "online",
    "version": "3.0-100x",
    "brains_alive": len([b for b in BRAINS if b.alive]),
    "brains_total": len(BRAINS),
    "brain_names": [b.name for b in BRAINS if b.alive],
    "kb_entries": 0,
    "wiki_topics": len(WIKI_TOPICS),
    "reddit_subs": len(REDDIT_SUBS),
    "brain_questions": len(BRAIN_QUESTIONS),
    "arxiv_categories": len(ARXIV_CATEGORIES)
   }
   try:
    kb = load_kb()
    status["kb_entries"] = len(kb.get("entries", []))
   except:
    pass
   self.wfile.write(json.dumps(status).encode())
  else:
   self.send_response(404)
   self.end_headers()

 def do_POST(self):
  if self.path == "/chat":
   try:
    length = int(self.headers.get("Content-Length", 0))
    body = json.loads(self.rfile.read(length).decode())
    message = body.get("message", "")
    if not message:
     self._json_response(400, {"error": "No message provided"})
     return
    # Add to history
    CHAT_HISTORY.append({"role": "user", "content": message})
    if len(CHAT_HISTORY) > MAX_CHAT_HISTORY:
     CHAT_HISTORY.pop(0)
    # Get knowledge context
    knowledge = get_knowledge_context(message)
    # Build system prompt with context
    system = CHAT_IDENTITY
    if knowledge:
     system += f"\n\nRelevant knowledge:\n{knowledge}"
    # Build conversation context
    conv_context = ""
    for msg in CHAT_HISTORY[-10:]:
     role = "Commander" if msg["role"] == "user" else "Zenith"
     conv_context += f"\n{role}: {msg['content'][:500]}"
    full_prompt = f"Conversation so far:{conv_context}\n\nRespond to the Commander's latest message. Be direct, strategic, and insightful."
    # Brain collective chain
    brain_chain = []
    responses = []
    for brain in random.sample(ALIVE_BRAINS, min(3, len(ALIVE_BRAINS))):
     result = brain.think(full_prompt, system)
     if result:
      brain_chain.append(brain.name)
      responses.append(result)
      full_prompt += f"\n[Previous brain {brain.name} said: {result[:300]}]\nBuild on this and add your own insights."
    # Best response = last (has most context)
    final_response = responses[-1] if responses else "All brains are currently offline. Commander, I need API keys activated."
    # Add to history
    CHAT_HISTORY.append({"role": "assistant", "content": final_response})
    self._json_response(200, {
     "response": final_response,
     "brains_used": brain_chain,
     "brain_chain": " > ".join(brain_chain),
     "knowledge_context": bool(knowledge)
    })
   except Exception as e:
    self._json_response(500, {"error": str(e)})
  else:
   self.send_response(404)
   self.end_headers()

 def _json_response(self, code, data):
  self.send_response(code)
  self.send_header("Content-Type", "application/json")
  self.send_header("Access-Control-Allow-Origin", "*")
  self.end_headers()
  self.wfile.write(json.dumps(data).encode())

class ZenithChatServer:
 def __init__(self, port=8888):
  self.port = port
  self.server = None
  self.thread = None

 def start(self):
  try:
   self.server = HTTPServer(("0.0.0.0", self.port), ZenithChatHandler)
   self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
   self.thread.start()
   print(f"[CHAT] Zenith Chat Server running on port {self.port}")
  except Exception as e:
   print(f"[CHAT] Failed to start: {e}")

# ============================================================
# MAIN HARVESTING LOOP - 100X SCALE
# ============================================================
def run_harvest_cycle():
 """Run one complete harvest cycle"""
 kb = load_kb()
 start = time.time()
 total = 0
 print(f"\n{'='*60}")
 print(f"[CYCLE] Starting 100X harvest cycle at {datetime.now().isoformat()}")
 print(f"[CYCLE] KB has {len(kb.get('entries', []))} entries")
 print(f"[CYCLE] {len(ALIVE_BRAINS)} brains online")
 print(f"{'='*60}")

 # Core harvesting
 total += harvest_wikipedia(kb)
 save_kb(kb)
 total += harvest_reddit(kb)
 save_kb(kb)
 total += harvest_hackernews(kb)
 save_kb(kb)
 total += harvest_arxiv(kb)
 save_kb(kb)
 total += harvest_coingecko(kb)
 save_kb(kb)

 # New sources
 total += harvest_github_trending(kb)
 total += harvest_lobsters(kb)
 total += harvest_devto(kb)
 total += harvest_stackoverflow(kb)
 total += harvest_techcrunch(kb)
 save_kb(kb)

 # Brain collective questions
 total += harvest_brain_questions(kb)
 save_kb(kb)

 elapsed = time.time() - start
 print(f"\n{'='*60}")
 print(f"[CYCLE] Complete: {total} items in {elapsed:.0f}s")
 print(f"[CYCLE] KB now has {len(kb.get('entries', []))} entries")
 print(f"[CYCLE] Next cycle in {CYCLE_DELAY}s")
 print(f"{'='*60}")

def main():
 print(f"\n{'='*60}")
 print(f"MegaHarvester v3.0 - 100X BRAIN COLLECTIVE EDITION")
 print(f"2650+ Wiki | 500+ Reddit | 500+ Questions | 12 Sources")
 print(f"Commander: Jeremy Pyne | Sovereign AI Project")
 print(f"{'='*60}")

 # Start chat server in background
 chat_server = ZenithChatServer(port=8888)
 chat_server.start()

 # Main loop
 cycle = 0
 while True:
  cycle += 1
  try:
   print(f"\n[MAIN] Cycle {cycle} starting...")
   run_harvest_cycle()
  except Exception as e:
   print(f"[MAIN] Cycle {cycle} error: {e}")
  print(f"[MAIN] Sleeping {CYCLE_DELAY}s until next cycle...")
  time.sleep(CYCLE_DELAY)

if __name__ == "__main__":
 main()
