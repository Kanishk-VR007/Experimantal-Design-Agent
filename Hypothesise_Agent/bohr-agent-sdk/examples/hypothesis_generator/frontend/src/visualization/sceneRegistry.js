/**
 * Experiment Template Registry
 * Maps experimental domains and templates to visualization configurations.
 */

export const SCENE_REGISTRY = {
  simple_pendulum: {
    domain: 'physics',
    label: 'Damped Harmonic Pendulum',
    icon: '⚛️',
    description: 'Dynamic non-linear pendulum with string tension, velocity vectors, and period telemetry.',
    defaultCamera: { position: [0.0, 1.8, 4.2], target: [0.0, 1.2, 0.0] },
    supportsVectors: true,
    supportsTimeline: true,
  },
  projectile_motion: {
    domain: 'physics',
    label: 'Ballistic Projectile Motion',
    icon: '🎯',
    description: 'Kinematic 2D trajectory with parabolic guide ribbon, velocity vector, and range readouts.',
    defaultCamera: { position: [0.0, 2.5, 7.5], target: [0.0, 1.2, 0.0] },
    supportsVectors: true,
    supportsTimeline: true,
  },
  molecular_geometry: {
    domain: 'chemistry',
    label: '3D Molecular Geometry',
    icon: '🧪',
    description: 'Interactive Cartesian molecular structure with CPK color convention and bond lengths.',
    defaultCamera: { position: [0.0, 1.2, 3.8], target: [0.0, 0.0, 0.0] },
    supportsVectors: false,
    supportsTimeline: true,
  },
  beam_deformation: {
    domain: 'civil_engineering',
    label: 'Beam Bending & Stress Profile',
    icon: '🏗️',
    description: 'Euler-Bernoulli beam deflection under transverse loading with flexural stress color gradient.',
    defaultCamera: { position: [0.0, 1.2, 6.5], target: [0.0, 0.0, 0.0] },
    supportsVectors: true,
    supportsTimeline: true,
  },
  gear_train: {
    domain: 'mechanical_engineering',
    label: 'Spur Gear Transmission',
    icon: '⚙️',
    description: 'Meshed mechanical spur gear train with synchronized counter-rotation and ratio reduction.',
    defaultCamera: { position: [0.8, 1.5, 3.5], target: [0.8, 0.4, 0.0] },
    supportsVectors: false,
    supportsTimeline: true,
  },
  arduino_circuit: {
    domain: 'electronics',
    label: 'Microcontroller Virtual Circuit',
    icon: '⚡',
    description: '3D development board, breadboard, current limiting resistor, and pulse-animated indicator LED.',
    defaultCamera: { position: [0.0, 1.8, 2.5], target: [0.0, 0.1, 0.0] },
    supportsVectors: false,
    supportsTimeline: true,
  },
  generic_apparatus: {
    domain: 'general',
    label: 'Scientific Test Apparatus',
    icon: '🔬',
    description: 'Laboratory measurement stage and holographic telemetry for custom or unclassified experiments.',
    defaultCamera: { position: [0.0, 1.8, 3.2], target: [0.0, 0.75, 0.0] },
    supportsVectors: false,
    supportsTimeline: true,
  },
}

export function getTemplateMeta(templateKey) {
  return SCENE_REGISTRY[templateKey] || SCENE_REGISTRY.generic_apparatus
}

