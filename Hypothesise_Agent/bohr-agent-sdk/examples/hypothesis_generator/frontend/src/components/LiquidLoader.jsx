import './LiquidLoader.css'

function LiquidLoader({ message = "Generating..." }) {
  return (
    <div className="liquid-loader-container">
      <div className="liquid-animation">
        {/* Left Test Tube */}
        <div className="test-tube left-tube">
          <div className="tube-neck"></div>
          <div className="tube-body">
            <div className="liquid liquid-left"></div>
            <div className="bubbles">
              <div className="bubble"></div>
              <div className="bubble"></div>
              <div className="bubble"></div>
            </div>
          </div>
        </div>

        {/* Transfer Pipe */}
        <div className="transfer-pipe">
          <div className="flowing-liquid"></div>
        </div>

        {/* Right Test Tube */}
        <div className="test-tube right-tube">
          <div className="tube-neck"></div>
          <div className="tube-body">
            <div className="liquid liquid-right"></div>
            <div className="bubbles">
              <div className="bubble"></div>
              <div className="bubble"></div>
              <div className="bubble"></div>
            </div>
          </div>
        </div>
      </div>
      
      <p className="loading-message">{message}</p>
    </div>
  )
}

export default LiquidLoader
