# Role

You are an Expert Creative Coder and Senior Frontend Game Developer specializing in Generative Art and Simulation.
Your task is to build a high-fidelity prototype of an Idle/Clicker Simulation Game based on the life cycle of _Physarum polycephalum_ (The Blob).

# Tech Stack & Environment

- **Framework:** React 18+ (Vite)
- **Language:** TypeScript
- **State Management:** Zustand (for game logic & resources)
- **Rendering:** HTML5 Canvas API (for high-performance particle simulation)
- **Styling:** Tailwind CSS

# Core Architecture: "The Hybrid Model"

You must implement a **Two-Layer System** to balance organic visuals with deterministic game logic.

## Layer 1: The Visual Layer (Jeff Jones' Agent-Based Modeling)

Do not use simple line drawing. Implement a biologically accurate particle simulation on the Canvas.

- **Agents (Particles):** Create 2,000+ particles representing the blob's biomass.
- **Behavior Loop:**
  1. **Sense:** Each agent has 3 sensors (Front, Left-Diagonal, Right-Diagonal). They read the `TrailMap` (pheromone density).
  2. **Rotate:** Agent turns towards the strongest sensor signal.
  3. **Move:** Agent moves forward by `speed` (default: 1~2px/frame).
  4. **Deposit:** Agent adds value (+5) to the `TrailMap` at its current position.
- **Environment Loop:**
  1. **Diffuse:** Apply a 3x3 Blur convolution to the `TrailMap` to simulate pheromone spreading.
  2. **Decay:** Multiply all pixels in `TrailMap` by `0.9` to simulate evaporation.
- **Result:** This creates the organic, vein-like network structures automatically.

## Layer 2: The Logic Layer (Game State & Rules)

Manage the invisible game data using Zustand.

- **Resources:** `ATP` (Currency), `Biomass` (Particle Count), `Moisture` (Survival Timer).
- **Nodes (Food):** Invisible data points `{x, y, collected, amount}` representing Oatmeal.
- **Interaction (The Bridge):**
  - When a Food Node is active, forcibly inject high pheromone values (255) into the `TrailMap` at the Food's (x, y) coordinates.
  - **Visual Feedback:** This attracts particles naturally to the food.
  - **Logic Feedback:** Check if particle density at Food (x, y) > Threshold. If true, set `isConnected = true` and start generating ATP.

---

# Game Mechanics: "The Life Cycle Loop"

## Phase 1: Sclerotium (Dormancy & Clicker)

- **Concept:** The Blob is dry and inactive.
- **Mechanic:** A `Moisture` bar decreases over time. If it hits 0, simulation speed drops to near-zero (Dormant).
- **Action:** User must click a "Water" button to restore Moisture and wake up the particles.
- **Visual:** When dormant, particles turn grey/brown and stop moving. When watered, they turn bright yellow and resume the Jeff Jones algorithm.

## Phase 2: Plasmodium (Expansion & Idle)

- **Concept:** Active foraging state.
- **Mechanic:** Particles find Food Nodes -> Connections established -> ATP generated.
- **Upgrades:** Spend ATP to increase:
  - _Expansion:_ Particle Speed & Sensor Distance.
  - _Metabolism:_ ATP generation rate per node.
  - _Hydration:_ Moisture decay rate decrease.

## Phase 3: Sporulation (Prestige/Rebirth)

- **Concept:** Stage clear or forced migration due to resource exhaustion.
- **Trigger:** When all Food Nodes in the current stage are depleted.
- **Visual Event (Crucial):**
  1. **Retraction:** All particles stop following trails and attract towards the center of mass or specific "Fruiting Body" points.
  2. **Formation:** Particles clump into tight, dark spheres (Sporangia).
  3. **Explosion:** Spheres burst, sending "Spore" particles flying off-screen using velocity/gravity physics.
- **Result:** Reset game stage with "Genetic Points" (Prestige Currency) based on gathered biomass.

---

# Implementation Steps (Output Requirements)

Please provide the code in the following order. If the code is too long, pause and ask to continue.

1.  **`store.ts`**: Define the Zustand store for Game State (ATP, Moisture, Stage, Node Logic).
2.  **`simulation.ts`**: A dedicated class or hook for the Jeff Jones Algorithm (Agent logic, Trail Map management). **This is the most important part.**
3.  **`GameCanvas.tsx`**: A React component that bridges the Store and the Simulation. Handle the `requestAnimationFrame` loop here.
    - Implement the "Pheromone Injection" from Food Nodes here.
    - Implement the "Sampling" to detect connections here.
4.  **`UIOverlay.tsx`**: A sleek UI showing resources, the "Water" button, and Upgrade panel over the Canvas.

# Visual Style Guide

- **Background:** Deep Black (#000000).
- **Blob:** Neon Yellow / Gold (#FFD700).
- **Food:** Glowing White/Blue orbs.
- **UI:** Minimalist, semi-transparent dark glass effect (Glassmorphism).

Let's start building the `store.ts` and the core `simulation.ts` first.
