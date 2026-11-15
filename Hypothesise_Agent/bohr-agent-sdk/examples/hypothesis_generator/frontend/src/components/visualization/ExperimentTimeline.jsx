import React from 'react'

export function ExperimentTimeline({
  currentTime,
  duration,
  isPlaying,
  playbackSpeed,
  loop,
  onPlayPause,
  onReset,
  onScrub,
  onStep,
  onChangeSpeed,
  onToggleLoop,
}) {
  const progressPercent = duration > 0 ? (currentTime / duration) * 100 : 0

  return (
    <div className="vis-timeline-bar">
      <div className="vis-timeline-controls">
        {/* Reset */}
        <button
          className="vis-btn vis-btn-icon"
          title="Reset to Start (0s)"
          onClick={onReset}
        >
          ⏮
        </button>

        {/* Step Back */}
        <button
          className="vis-btn vis-btn-icon"
          title="Step Backward (-0.1s)"
          onClick={() => onStep(-0.1)}
        >
          ⏪
        </button>

        {/* Play / Pause */}
        <button
          className={`vis-btn vis-btn-play ${isPlaying ? 'is-playing' : ''}`}
          title={isPlaying ? 'Pause' : 'Play'}
          onClick={onPlayPause}
        >
          {isPlaying ? '⏸ Pause' : '▶ Play'}
        </button>

        {/* Step Forward */}
        <button
          className="vis-btn vis-btn-icon"
          title="Step Forward (+0.1s)"
          onClick={() => onStep(0.1)}
        >
          ⏩
        </button>

        {/* Time Readout */}
        <div className="vis-time-display">
          <span className="vis-time-current">{currentTime.toFixed(2)}s</span>
          <span className="vis-time-sep">/</span>
          <span className="vis-time-duration">{duration.toFixed(2)}s</span>
        </div>
      </div>

      {/* Scrubber Slider */}
      <div className="vis-slider-container">
        <input
          type="range"
          min="0"
          max={duration || 1}
          step="0.01"
          value={currentTime}
          onChange={(e) => onScrub(parseFloat(e.target.value))}
          className="vis-timeline-slider"
          style={{
            background: `linear-gradient(to right, #38bdf8 0%, #38bdf8 ${progressPercent}%, #334155 ${progressPercent}%, #334155 100%)`,
          }}
        />
      </div>

      <div className="vis-timeline-extras">
        {/* Playback Speed Multiplier */}
        <div className="vis-speed-selector">
          <label>Speed:</label>
          <select
            value={playbackSpeed}
            onChange={(e) => onChangeSpeed(parseFloat(e.target.value))}
            className="vis-select"
          >
            <option value={0.25}>0.25x</option>
            <option value={0.5}>0.5x</option>
            <option value={1}>1.0x</option>
            <option value={1.5}>1.5x</option>
            <option value={2}>2.0x</option>
          </select>
        </div>

        {/* Loop Toggle */}
        <button
          className={`vis-btn vis-btn-toggle ${loop ? 'is-active' : ''}`}
          title="Loop Playback"
          onClick={onToggleLoop}
        >
          🔁 Loop
        </button>
      </div>
    </div>
  )
}

