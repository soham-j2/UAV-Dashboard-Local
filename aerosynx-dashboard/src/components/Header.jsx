function Header({ data }) {

  const source =
    data?.source || {};

  const hardwareCount =
    Object.values(source)
      .filter((value) => value === "HW")
      .length;

  const simulatedCount =
    Object.values(source)
      .filter((value) => value === "SIM")
      .length;


  return (

    <header className="top-header">

      <div className="brand">

        <img
          src="/logo.png"
          alt="AeroSynX Logo"
          style={{
            height: "44px",
            width: "auto",
            objectFit: "contain",
            marginRight: "10px",
            filter: "drop-shadow(0 0 8px rgba(255, 170, 0, 0.25))"
          }}
        />

        <div>

          <h2>
            AeroSynX
          </h2>

          <span>
            IDEAS TODAY • DEFENCE TOMORROW
          </span>

        </div>

      </div>



      <div className="telemetry-status">

        <div className="telemetry-item">

          <span className="status-dot green" />

          Hardware

          <strong>
            {hardwareCount}
          </strong>

        </div>


        <div className="telemetry-item">

          <span className="status-dot blue" />

          Simulated

          <strong>
            {simulatedCount}
          </strong>

        </div>


        <div className="connection">

          <span className="status-dot green" />

          API Connected

        </div>

      </div>

    </header>

  );

}


export default Header;