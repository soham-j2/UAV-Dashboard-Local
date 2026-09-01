import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import UAVNewModel from "./components/newmodel";
import "./App.css";

import {
  ToastContainer,
  toast,
} from "react-toastify";

import "react-toastify/dist/ReactToastify.css";

/* ============================================================
   AEROSYNX UAV DIGITAL TWIN COMMAND CENTER
   ============================================================

   BACKEND
      |
      | WebSocket
      v
   ws://localhost:8080/telemetry
      |
      v
   App.jsx
      |
      v
   UAVNewModel

   FAULT INJECTION
      |
      | POST
      v
   /api/fault/inject

   FAULT CLEAR
      |
      | POST
      v
   /api/fault/clear
   ============================================================ */


/* ============================================================
   CONFIGURATION
   ============================================================ */

const WS_URL =
  import.meta.env.VITE_WS_URL ||
  "ws://localhost:8080/telemetry";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "https://virtual-engine-api.onrender.com";

const FAULT_INJECT_URL =
  `${API_BASE}/api/fault/inject`;

const FAULT_CLEAR_URL =
  `${API_BASE}/api/fault/clear`;


/* ============================================================
   DEFAULT TELEMETRY
   ============================================================ */

const DEFAULT_READING = {
  rpm: 0,
  cht_c: 25,
  egt_c: 25,
  oil_press_bar: 0,
  oil_temp_c: 25,
  fuel_flow_lph: 0,
  vibration_g: 0,
  battery_v: 12,
  injection_deg: 0,
  roll_deg: 0,
  pitch_deg: 0,
  yaw_deg: 0,
};

const DEFAULT_PACKET = {
  reading: DEFAULT_READING,

  source: {},

  range_status: {},

  possible_faults: [],

  context: {
    active_fault: "none",
    mission_profile: "normal_cruise",
  },

  api: {
    connected: false,
  },
};


/* ============================================================
   FAULT DEFINITIONS
   ============================================================ */

const FAULTS = [
  {
    id: "none",
    name: "No Fault",
    short: "NOMINAL",
    description: "Normal engine operation",
    severity: "normal",
  },

  {
    id: "misfire",
    name: "Misfire",
    short: "MISFIRE",
    description:
      "Combustion interruption / unstable firing",
    severity: "critical",
  },

  {
    id: "injector_abnormality",
    name: "Injector Abnormality",
    short: "INJECTOR",
    description:
      "Fuel injection abnormality",
    severity: "warning",
  },

  {
    id: "coking_degradation",
    name: "Coking Degradation",
    short: "COKING",
    description:
      "Deposit / thermal degradation",
    severity: "warning",
  },

  {
    id: "lubrication_issue",
    name: "Lubrication Issue",
    short: "LUBRICATION",
    description:
      "Low oil pressure / high oil temperature",
    severity: "critical",
  },

  {
    id: "sensor_drift",
    name: "Sensor Drift",
    short: "SENSOR DRIFT",
    description:
      "Sensor output deviation",
    severity: "warning",
  },

  {
    id: "combustion_instability",
    name: "Combustion Instability",
    short: "COMBUSTION",
    description:
      "Unstable combustion process",
    severity: "critical",
  },

  {
    id: "battery_alternator_health",
    name: "Battery / Alternator Health",
    short: "ELECTRICAL",
    description:
      "Charging system abnormality",
    severity: "warning",
  },

  {
    id: "injection_timing_issue",
    name: "Injection Timing Issue",
    short: "TIMING",
    description:
      "Injection timing outside expected range",
    severity: "critical",
  },
];


/* ============================================================
   MISSION PROFILES
   ============================================================ */

const MISSION_PROFILES = [
  {
    id: "normal_cruise",
    name: "Normal Cruise",
    icon: "✦",
  },

  {
    id: "high_altitude",
    name: "High Altitude",
    icon: "◈",
  },

  {
    id: "hot_weather",
    name: "Hot Weather",
    icon: "☀",
  },

  {
    id: "rapid_throttle",
    name: "Rapid Throttle",
    icon: "⚡",
  },
];


/* ============================================================
   ENGINE OPERATING RANGES
   ============================================================ */

const RANGES = {
  rpm: [4800, 5300],

  cht_c: [95, 125],

  egt_c: [620, 720],

  oil_press_bar: [2.5, 4.2],

  oil_temp_c: [85, 105],

  fuel_flow_lph: [14, 18],

  vibration_g: [0.05, 0.15],

  battery_v: [13.8, 14.4],

  injection_deg: [20, 25],
};


/* ============================================================
   HELPERS
   ============================================================ */

function number(value, fallback = 0) {
  const n = Number(value);

  return Number.isFinite(n)
    ? n
    : fallback;
}


function format(value, digits = 1) {
  return number(value).toFixed(digits);
}


function clamp(value, min, max) {
  return Math.max(
    min,
    Math.min(max, value)
  );
}


function normalize(value, min, max) {
  if (max === min) return 0;

  return clamp(
    (number(value) - min) /
      (max - min),
    0,
    1
  );
}


function rangeStatus(field, value) {
  if (!RANGES[field]) {
    return "unknown";
  }

  const [min, max] =
    RANGES[field];

  const n = number(value);

  if (
    n < min ||
    n > max
  ) {
    return "danger";
  }

  const span = max - min;

  const warningMargin =
    span * 0.12;

  if (
    n <= min + warningMargin ||
    n >= max - warningMargin
  ) {
    return "warning";
  }

  return "normal";
}


function faultDetails(id) {
  return (
    FAULTS.find(
      (fault) =>
        fault.id === id
    ) || FAULTS[0]
  );
}


function prettyFault(id) {
  if (
    !id ||
    id === "none"
  ) {
    return "NOMINAL";
  }

  return id
    .replaceAll("_", " ")
    .toUpperCase();
}


/* ============================================================
   TELEMETRY NORMALIZATION
   ============================================================ */

function normalizePacket(raw) {
  if (
    !raw ||
    typeof raw !== "object"
  ) {
    return DEFAULT_PACKET;
  }

  const reading = {
    ...DEFAULT_READING,
    ...(raw.reading || {}),
  };

  const context = {
    active_fault:
      raw.context?.active_fault ??
      raw.active_fault ??
      "none",

    mission_profile:
      raw.context?.mission_profile ??
      raw.mission_profile ??
      "normal_cruise",
  };

  return {
    ...DEFAULT_PACKET,

    ...raw,

    reading,

    source:
      raw.source || {},

    range_status:
      raw.range_status || {},

    possible_faults:
      raw.possible_faults || [],

    context,
  };
}


/* ============================================================
   SECTION HEADER
   ============================================================ */

function SectionHeader({
  eyebrow,
  title,
  right,
}) {
  return (
    <div className="section-header">

      <div>

        <div className="section-eyebrow">
          {eyebrow}
        </div>

        <div className="section-title">
          {title}
        </div>

      </div>

      {right && (
        <div className="section-right">
          {right}
        </div>
      )}

    </div>
  );
}


/* ============================================================
   TELEMETRY CARD
   ============================================================ */

function TelemetryCard({
  label,
  value,
  unit,
  field,
  icon,
  compact = false,
}) {
  const status =
    rangeStatus(
      field,
      value
    );

  return (
    <div
      className={`
        telemetry-card
        telemetry-${status}
        ${compact ? "telemetry-compact" : ""}
      `}
    >

      <div className="telemetry-card-top">

        <span className="telemetry-icon">
          {icon}
        </span>

        <span className="telemetry-label">
          {label}
        </span>

        <span
          className={`
            telemetry-dot
            dot-${status}
          `}
        />

      </div>

      <div className="telemetry-value">
        {format(value)}
      </div>

      <div className="telemetry-unit">
        {unit}
      </div>

      <div className="telemetry-mini-bar">

        <div
          style={{
            width: `${
              normalize(
                value,
                ...(RANGES[field] || [
                  0,
                  100,
                ])
              ) * 100
            }%`,
          }}
        />

      </div>

    </div>
  );
}


/* ============================================================
   SOURCE BADGE
   ============================================================ */

function SourceBadge({
  value,
}) {
  const isHardware =
    value === "HW" ||
    value === "REAL HARDWARE" ||
    value ===
      "REAL HARDWARE / API";

  return (
    <span
      className={`
        source-badge
        ${
          isHardware
            ? "source-hw"
            : "source-sim"
        }
      `}
    >
      {isHardware
        ? "HW"
        : "SIM"}
    </span>
  );
}


/* ============================================================
   HEALTH RING
   ============================================================ */

function HealthRing({
  health,
}) {
  const radius = 44;

  const circumference =
    2 * Math.PI * radius;

  const offset =
    circumference -
    (clamp(
      health,
      0,
      100
    ) /
      100) *
      circumference;

  let state = "HEALTHY";

  if (health < 70) {
    state = "CAUTION";
  }

  if (health < 45) {
    state = "CRITICAL";
  }

  return (
    <div className="health-ring-wrapper">

      <svg
        className="health-ring"
        width="120"
        height="120"
        viewBox="0 0 120 120"
      >

        <circle
          className="health-ring-bg"
          cx="60"
          cy="60"
          r={radius}
        />

        <circle
          className={`
            health-ring-progress
            health-${state.toLowerCase()}
          `}
          cx="60"
          cy="60"
          r={radius}
          strokeDasharray={
            circumference
          }
          strokeDashoffset={
            offset
          }
        />

      </svg>

      <div className="health-ring-content">

        <strong>
          {Math.round(health)}
        </strong>

        <span>
          %
        </span>

      </div>

      <div className="health-ring-label">
        {state}
      </div>

    </div>
  );
}


/* ============================================================
   LIVE GRAPH
   ============================================================ */

function LiveGraph({
  data,
  min,
  max,
}) {
  const width = 420;
  const height = 100;

  const points = data
    .slice(-40)
    .map(
      (
        value,
        index,
        arr
      ) => {
        const x =
          arr.length <= 1
            ? 0
            : (index /
                (arr.length - 1)) *
              width;

        const y =
          height -
          normalize(
            value,
            min,
            max
          ) *
            (height - 10) -
          5;

        return `${x},${y}`;
      }
    )
    .join(" ");

  return (
    <svg
      className="live-graph"
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
    >

      <line
        x1="0"
        y1="25"
        x2={width}
        y2="25"
        className="graph-grid"
      />

      <line
        x1="0"
        y1="50"
        x2={width}
        y2="50"
        className="graph-grid"
      />

      <line
        x1="0"
        y1="75"
        x2={width}
        y2="75"
        className="graph-grid"
      />

      {points && (
        <polyline
          points={points}
          fill="none"
          className="graph-line"
        />
      )}

    </svg>
  );
}


/* ============================================================
   FAULT INJECTION PANEL
   ============================================================ */

function FaultInjection({
  selectedFault,
  setSelectedFault,
  selectedProfile,
  setSelectedProfile,
  onInject,
  onClear,
  injecting,
}) {
  const selected =
    faultDetails(
      selectedFault
    );

  return (
    <div className="fault-panel">

      <SectionHeader
        eyebrow="SCENARIO CONTROL"
        title="FAULT INJECTION"
        right={
          <span className="simulation-chip">
            SIMULATION
          </span>
        }
      />

      <div className="fault-warning">

        <div className="fault-warning-icon">
          !
        </div>

        <div>

          <strong>
            DIGITAL TWIN TEST MODE
          </strong>

          <p>
            Inject a controlled
            engine fault and
            observe the
            corresponding
            virtual engine
            response.
          </p>

        </div>

      </div>


      <div className="control-label">
        SELECT FAILURE MODE
      </div>


      <select
        className="fault-select"
        value={selectedFault}
        onChange={(e) =>
          setSelectedFault(
            e.target.value
          )
        }
      >

        {FAULTS.map(
          (fault) => (
            <option
              key={fault.id}
              value={fault.id}
            >
              {fault.name}
            </option>
          )
        )}

      </select>


      <div className="fault-description">

        <div
          className={`
            severity-marker
            severity-${selected.severity}
          `}
        />

        <div>

          <strong>
            {selected.name}
          </strong>

          <span>
            {selected.description}
          </span>

        </div>

      </div>


      <div className="control-label">
        MISSION PROFILE
      </div>


      <div className="profile-grid">

        {MISSION_PROFILES.map(
          (profile) => (
            <button
              type="button"
              key={profile.id}
              className={`
                profile-button
                ${
                  selectedProfile ===
                  profile.id
                    ? "profile-active"
                    : ""
                }
              `}
              onClick={() =>
                setSelectedProfile(
                  profile.id
                )
              }
            >

              <span>
                {profile.icon}
              </span>

              {profile.name}

            </button>
          )
        )}

      </div>


      <div className="fault-actions">

        <button
          type="button"
          className="inject-button"
          onClick={onInject}
          disabled={injecting}
        >

          <span className="inject-icon">
            {injecting
              ? "◌"
              : "⚠"}
          </span>

          {injecting
            ? "INJECTING..."
            : "INJECT FAULT"}

        </button>


        <button
          type="button"
          className="clear-button"
          onClick={onClear}
          disabled={injecting}
        >
          CLEAR
        </button>

      </div>

    </div>
  );
}


/* ============================================================
   APP
   ============================================================ */

export default function App() {

  const [
    packet,
    setPacket,
  ] = useState(
    DEFAULT_PACKET
  );


  const [
    connected,
    setConnected,
  ] = useState(false);


  const [
    lastUpdate,
    setLastUpdate,
  ] = useState(null);


  const [
    selectedFault,
    setSelectedFault,
  ] = useState("none");


  const [
    selectedProfile,
    setSelectedProfile,
  ] = useState(
    "normal_cruise"
  );


  const [
    injecting,
    setInjecting,
  ] = useState(false);


  const [
    alarmActive,
    setAlarmActive,
  ] = useState(false);


  const [
    rpmHistory,
    setRpmHistory,
  ] = useState([]);


  const [
    egtHistory,
    setEgtHistory,
  ] = useState([]);


  const socketRef =
    useRef(null);

  const reconnectRef =
    useRef(null);

  const alarmTimerRef =
    useRef(null);


  const reading =
    packet.reading ||
    DEFAULT_READING;


  const context =
    packet.context ||
    {};


  const activeFault =
    context.active_fault ||
    "none";


  const missionProfile =
    context.mission_profile ||
    "normal_cruise";


  const activeFaultInfo =
    faultDetails(
      activeFault
    );


  const engineRunning =
    number(reading.rpm) >
    200;


  /* ==========================================================
     HEALTH CALCULATION
     ========================================================== */

  const health = useMemo(() => {

    let score = 100;

    const checks = [

      [
        "rpm",
        reading.rpm,
      ],

      [
        "cht_c",
        reading.cht_c,
      ],

      [
        "egt_c",
        reading.egt_c,
      ],

      [
        "oil_press_bar",
        reading.oil_press_bar,
      ],

      [
        "oil_temp_c",
        reading.oil_temp_c,
      ],

      [
        "fuel_flow_lph",
        reading.fuel_flow_lph,
      ],

      [
        "vibration_g",
        reading.vibration_g,
      ],

      [
        "battery_v",
        reading.battery_v,
      ],

      [
        "injection_deg",
        reading.injection_deg,
      ],
    ];


    checks.forEach(
      ([field, value]) => {

        const status =
          rangeStatus(
            field,
            value
          );

        if (
          status ===
          "danger"
        ) {
          score -= 8;
        }

        if (
          status ===
          "warning"
        ) {
          score -= 2;
        }

      }
    );


    if (
      activeFault !==
      "none"
    ) {

      const info =
        faultDetails(
          activeFault
        );

      if (
        info.severity ===
        "critical"
      ) {
        score -= 20;
      } else {
        score -= 10;
      }

    }


    return clamp(
      score,
      0,
      100
    );

  }, [
    reading,
    activeFault,
  ]);


  /* ==========================================================
     WEBSOCKET CONNECTION
     ========================================================== */

  const connectWebSocket =
    useCallback(() => {

      if (
        socketRef.current
      ) {

        try {
          socketRef.current.close();
        } catch {
          // Ignore
        }

      }


      let ws;


      try {

        ws =
          new WebSocket(
            WS_URL
          );

      } catch {

        setConnected(
          false
        );

        reconnectRef.current =
          setTimeout(
            connectWebSocket,
            3000
          );

        return;
      }


      socketRef.current =
        ws;


      ws.onopen = () => {

        console.log(
          "[AeroSynX] Telemetry connected"
        );

        setConnected(
          true
        );

        toast.success(
          "Telemetry connection established",
          {
            toastId:
              "telemetry-connected",
          }
        );

      };


      ws.onmessage = (
        event
      ) => {

        try {

          const raw =
            JSON.parse(
              event.data
            );


          const normalized =
            normalizePacket(
              raw
            );


          setPacket(
            normalized
          );


          setLastUpdate(
            new Date()
          );


          const r =
            normalized.reading;


          setRpmHistory(
            (prev) =>
              [
                ...prev,
                number(r.rpm),
              ].slice(-50)
          );


          setEgtHistory(
            (prev) =>
              [
                ...prev,
                number(r.egt_c),
              ].slice(-50)
          );

        } catch (error) {

          console.warn(
            "[AeroSynX] Invalid telemetry:",
            error
          );

        }

      };


      ws.onerror = () => {

        console.warn(
          "[AeroSynX] Telemetry socket error"
        );

        setConnected(
          false
        );

      };


      ws.onclose = () => {

        setConnected(
          false
        );

        reconnectRef.current =
          setTimeout(
            connectWebSocket,
            3000
          );

      };

    }, []);


  useEffect(() => {

    connectWebSocket();

    const fetchHttpTelemetry = async () => {
      try {
        const response = await fetch("http://127.0.0.1:5000/api/dashboard");
        if (response.ok) {
          const raw = await response.json();
          const normalized = normalizePacket(raw);
          setPacket(normalized);
          setConnected(true);
          setLastUpdate(new Date());

          const r = normalized.reading;
          if (r) {
            setRpmHistory((prev) =>
              [...prev, number(r.rpm)].slice(-50)
            );
            setEgtHistory((prev) =>
              [...prev, number(r.egt_c)].slice(-50)
            );
          }
        }
      } catch (err) {
        // Backend offline or unreachable
      }
    };

    fetchHttpTelemetry();
    const pollInterval = setInterval(fetchHttpTelemetry, 150);


    return () => {
      clearInterval(pollInterval);

      if (
        reconnectRef.current
      ) {

        clearTimeout(
          reconnectRef.current
        );

      }


      if (
        socketRef.current
      ) {

        socketRef.current.close();

      }


      if (
        alarmTimerRef.current
      ) {

        clearTimeout(
          alarmTimerRef.current
        );

      }

    };

  }, [
    connectWebSocket,
  ]);



  /* ==========================================================
     FAULT ALARM
     ========================================================== */

  useEffect(() => {

    if (
      activeFault &&
      activeFault !==
        "none"
    ) {

      setAlarmActive(
        true
      );


      if (
        alarmTimerRef.current
      ) {

        clearTimeout(
          alarmTimerRef.current
        );

      }


      alarmTimerRef.current =
        setTimeout(() => {

          setAlarmActive(
            false
          );

        }, 10000);

    } else {

      setAlarmActive(
        false
      );

    }

  }, [
    activeFault,
  ]);


  /* ==========================================================
     AUDIO ALARM
     ========================================================== */

  const playAlarm =
    useCallback(() => {

      try {

        const AudioContext =
          window.AudioContext ||
          window.webkitAudioContext;


        if (
          !AudioContext
        ) {
          return;
        }


        const audio =
          new AudioContext();


        const start =
          audio.currentTime;


        for (
          let i = 0;
          i < 10;
          i++
        ) {

          const oscillator =
            audio.createOscillator();


          const gain =
            audio.createGain();


          oscillator.type =
            "square";


          oscillator.frequency.value =
            i % 2 === 0
              ? 880
              : 660;


          gain.gain.setValueAtTime(
            0.0001,
            start + i
          );


          gain.gain.exponentialRampToValueAtTime(
            0.16,
            start + i + 0.02
          );


          gain.gain.exponentialRampToValueAtTime(
            0.0001,
            start + i + 0.35
          );


          oscillator.connect(
            gain
          );

          gain.connect(
            audio.destination
          );


          oscillator.start(
            start + i
          );


          oscillator.stop(
            start + i + 0.4
          );

        }


        setTimeout(() => {

          audio.close();

        }, 11000);

      } catch (error) {

        console.warn(
          "Audio alarm unavailable",
          error
        );

      }

    }, []);


  /* ==========================================================
     INJECT FAULT
     ========================================================== */

  const injectFault =
    async () => {

      setInjecting(
        true
      );


      try {

        const response =
          await fetch(
            FAULT_INJECT_URL,
            {
              method:
                "POST",

              headers: {
                "Content-Type":
                  "application/json",
              },

              body:
                JSON.stringify({
                  fault:
                    selectedFault,

                  active_fault:
                    selectedFault,

                  mission_profile:
                    selectedProfile,
                }),
            }
          );


        if (
          !response.ok
        ) {

          throw new Error(
            `HTTP ${response.status}`
          );

        }


        const data =
          await response
            .json()
            .catch(
              () => null
            );


        console.log(
          "[AeroSynX] Fault injected:",
          data
        );


        /* ============================================
           REACT TOASTIFY SUCCESS
           ============================================ */

        if (
          selectedFault ===
          "none"
        ) {

          toast.success(
            "Engine returned to nominal state",
            {
              position:
                "top-right",
              autoClose:
                3000,
              theme:
                "dark",
            }
          );

        } else {

          toast.error(
            `${prettyFault(
              selectedFault
            )} injected successfully`,
            {
              position:
                "top-right",
              autoClose:
                4000,
              theme:
                "dark",
            }
          );

        }


        setAlarmActive(
          selectedFault !==
            "none"
        );


        if (
          selectedFault !==
          "none"
        ) {

          playAlarm();

        }

      } catch (error) {

        console.error(
          "[AeroSynX] Fault injection failed:",
          error
        );


        toast.error(
          "Fault injection failed. Check backend endpoint.",
          {
            position:
              "top-right",
            autoClose:
              4000,
            theme:
              "dark",
          }
        );

      } finally {

        setInjecting(
          false
        );

      }

    };


  /* ==========================================================
     CLEAR FAULT
     ========================================================== */

  const clearFault =
    async () => {

      setInjecting(
        true
      );


      try {

        const response =
          await fetch(
            FAULT_CLEAR_URL,
            {
              method:
                "POST",

              headers: {
                "Content-Type":
                  "application/json",
              },

              body:
                JSON.stringify({
                  fault:
                    "none",

                  active_fault:
                    "none",

                  mission_profile:
                    selectedProfile,
                }),
            }
          );


        if (
          !response.ok
        ) {

          throw new Error(
            `HTTP ${response.status}`
          );

        }


        toast.success(
          "Fault cleared — engine returning to nominal state",
          {
            position:
              "top-right",

            autoClose:
              3500,

            theme:
              "dark",
          }
        );


        setAlarmActive(
          false
        );

      } catch (error) {

        console.error(
          "[AeroSynX] Fault clear failed:",
          error
        );


        toast.error(
          "Could not clear fault. Check backend endpoint.",
          {
            position:
              "top-right",

            autoClose:
              4000,

            theme:
              "dark",
          }
        );

      } finally {

        setInjecting(
          false
        );

      }

    };


  /* ==========================================================
     SOURCE
     ========================================================== */

  const source =
    packet.source || {};


  /* ==========================================================
     TIME
     ========================================================== */

  const updateText =
    lastUpdate
      ? lastUpdate.toLocaleTimeString()
      : "--:--:--";


  /* ==========================================================
     RENDER
     ========================================================== */

  return (
    <div className="aerosynx-app">

      {/* ======================================================
          TOP COMMAND BAR
          ====================================================== */}

      <header className="top-command-bar">

        <div className="brand-block">

          <img
            src="/logo.png"
            alt="AeroSynX Logo"
            className="brand-img-logo"
            style={{
              height: "54px",
              width: "auto",
              objectFit: "contain",
              filter: "drop-shadow(0 0 10px rgba(255, 170, 0, 0.25))"
            }}
          />

          <div>

            <div className="brand-name">
              AEROSYNX
            </div>

            <div className="brand-subtitle">
              IDEAS TODAY • DEFENCE TOMORROW
            </div>

          </div>

        </div>



        <div className="mission-identity">

          <span className="identity-label">
            MISSION
          </span>

          <strong>
            DF-UAS-01
          </strong>

          <span className="identity-divider">
            /
          </span>

          <span>
            PISTON PROPULSION SYSTEM
          </span>

        </div>


        <div className="top-status">

          <div className="top-status-item">

            <span className="status-light green" />

            <div>

              <small>
                DIGITAL TWIN
              </small>

              <strong>
                ONLINE
              </strong>

            </div>

          </div>


          <div className="top-status-item">

            <span
              className={`
                status-light
                ${
                  connected
                    ? "green"
                    : "red"
                }
              `}
            />

            <div>

              <small>
                TELEMETRY
              </small>

              <strong>
                {connected
                  ? "LIVE"
                  : "OFFLINE"}
              </strong>

            </div>

          </div>


          <div className="utc-clock">
            {updateText}
          </div>

        </div>

      </header>


      {/* ======================================================
          MAIN GRID
          ====================================================== */}

      <main className="dashboard-grid">

        {/* ====================================================
            LEFT COLUMN
            ==================================================== */}

        <section className="left-column">


          {/* ENGINE READINESS */}

          <div className="panel readiness-panel">

            <SectionHeader
              eyebrow="SYSTEM MONITOR"
              title="ENGINE READINESS"
              right={
                <span className="live-chip">
                  ● LIVE
                </span>
              }
            />


            <div className="readiness-content">

              <HealthRing
                health={health}
              />


              <div className="readiness-stats">

                <div className="readiness-row">

                  <span>
                    ENGINE STATE
                  </span>

                  <strong
                    className={
                      engineRunning
                        ? "text-green"
                        : "text-red"
                    }
                  >
                    {engineRunning
                      ? "RUNNING"
                      : "OFFLINE"}
                  </strong>

                </div>


                <div className="readiness-row">

                  <span>
                    HEALTH INDEX
                  </span>

                  <strong>
                    {Math.round(
                      health
                    )}
                    /100
                  </strong>

                </div>


                <div className="readiness-row">

                  <span>
                    ACTIVE SCENARIO
                  </span>

                  <strong
                    className={
                      activeFault ===
                      "none"
                        ? "text-green"
                        : "text-danger"
                    }
                  >
                    {prettyFault(
                      activeFault
                    )}
                  </strong>

                </div>


                <div className="readiness-row">

                  <span>
                    PROFILE
                  </span>

                  <strong>
                    {missionProfile
                      .replaceAll(
                        "_",
                        " "
                      )
                      .toUpperCase()}
                  </strong>

                </div>

              </div>

            </div>


            <div className="system-bars">

              <div className="system-bar-row">

                <span>
                  ENGINE CORE
                </span>

                <div className="progress-track">

                  <div
                    style={{
                      width:
                        `${health}%`,
                    }}
                  />

                </div>

                <b>
                  {Math.round(
                    health
                  )}
                  %
                </b>

              </div>


              <div className="system-bar-row">

                <span>
                  SENSOR LINK
                </span>

                <div className="progress-track">

                  <div
                    style={{
                      width:
                        connected
                          ? "100%"
                          : "15%",
                    }}
                  />

                </div>

                <b>
                  {connected
                    ? "100%"
                    : "15%"}
                </b>

              </div>


              <div className="system-bar-row">

                <span>
                  DATA FUSION
                </span>

                <div className="progress-track">

                  <div
                    style={{
                      width:
                        "92%",
                    }}
                  />

                </div>

                <b>
                  92%
                </b>

              </div>

            </div>

          </div>


          {/* ENGINE TELEMETRY */}

          <div className="panel">

            <SectionHeader
              eyebrow="REAL-TIME DIAGNOSTICS"
              title="ENGINE TELEMETRY"
            />


            <div className="telemetry-grid">

              <TelemetryCard
                label="RPM"
                value={
                  reading.rpm
                }
                unit="REV/MIN"
                field="rpm"
                icon="◉"
              />


              <TelemetryCard
                label="CHT"
                value={
                  reading.cht_c
                }
                unit="°C"
                field="cht_c"
                icon="♨"
              />


              <TelemetryCard
                label="EGT"
                value={
                  reading.egt_c
                }
                unit="°C"
                field="egt_c"
                icon="♨"
              />


              <TelemetryCard
                label="OIL PRESS"
                value={
                  reading.oil_press_bar
                }
                unit="BAR"
                field="oil_press_bar"
                icon="◌"
              />


              <TelemetryCard
                label="OIL TEMP"
                value={
                  reading.oil_temp_c
                }
                unit="°C"
                field="oil_temp_c"
                icon="◇"
              />


              <TelemetryCard
                label="FUEL FLOW"
                value={
                  reading.fuel_flow_lph
                }
                unit="L/H"
                field="fuel_flow_lph"
                icon="⇩"
              />


              <TelemetryCard
                label="VIBRATION"
                value={
                  reading.vibration_g
                }
                unit="G"
                field="vibration_g"
                icon="⌁"
              />


              <TelemetryCard
                label="BATTERY"
                value={
                  reading.battery_v
                }
                unit="V"
                field="battery_v"
                icon="▣"
              />


              <TelemetryCard
                label="INJECTION"
                value={
                  reading.injection_deg
                }
                unit="DEG BTDC"
                field="injection_deg"
                icon="◈"
              />

            </div>

          </div>


          {/* LIVE GRAPHS */}

          <div className="panel graph-panel">

            <SectionHeader
              eyebrow="TREND ANALYSIS"
              title="THERMAL / SPEED RESPONSE"
              right={
                <span className="graph-legend">
                  <i />
                  LIVE FEED
                </span>
              }
            />


            <div className="graph-block">

              <div className="graph-title">

                <span>
                  ENGINE RPM
                </span>

                <strong>
                  {format(
                    reading.rpm,
                    0
                  )}
                </strong>

              </div>


              <LiveGraph
                data={
                  rpmHistory
                }
                min={4000}
                max={6000}
              />

            </div>


            <div className="graph-block">

              <div className="graph-title">

                <span>
                  EXHAUST GAS TEMPERATURE
                </span>

                <strong>
                  {format(
                    reading.egt_c
                  )}
                  °C
                </strong>

              </div>


              <LiveGraph
                data={
                  egtHistory
                }
                min={550}
                max={850}
              />

            </div>

          </div>

        </section>


        {/* ====================================================
            CENTER COLUMN
            ==================================================== */}

        <section className="center-column">


          {/* VIRTUAL ENGINE */}

          <div
            className={`
              panel
              twin-panel
              ${
                activeFault !==
                "none"
                  ? "twin-fault-active"
                  : ""
              }
            `}
          >

            <div className="twin-header">

              <div>

                <div className="section-eyebrow">
                  VIRTUAL ENGINE
                </div>

                <div className="twin-title">
                  3D DIGITAL TWIN
                </div>

              </div>


              <div className="twin-header-right">

                <div className="twin-mode">

                  <span className="status-light green" />

                  REACTIVE MODEL

                </div>


                <div className="twin-mode">

                  {connected
                    ? "200 MS"
                    : "--"}

                </div>

              </div>

            </div>


            {/* FAULT ALERT */}

            {activeFault !==
              "none" && (

              <div className="twin-fault-banner">

                <div className="fault-pulse">
                  !
                </div>

                <div>

                  <strong>
                    {prettyFault(
                      activeFault
                    )}
                  </strong>

                  <span>
                    FAULT DETECTED •
                    VIRTUAL ENGINE
                    RESPONSE ACTIVE
                  </span>

                </div>


                {alarmActive && (

                  <div className="alarm-badge">
                    ALARM
                  </div>

                )}

              </div>

            )}


            {/* 3D MODEL */}

            <div className="twin-view">

              <UAVNewModel
                packet={
                  packet
                }
                showOverlay={
                  false
                }
                width="100%"
                height="100%"
              />


              <div className="twin-corner top-left">
                AX / DT-01
              </div>


              <div className="twin-corner top-right">

                {engineRunning
                  ? "ENGINE LIVE"
                  : "ENGINE OFF"}

              </div>


              <div className="twin-corner bottom-left">
                DRAG TO ORBIT
              </div>


              <div className="twin-corner bottom-right">

                PITCH{" "}
                {format(
                  reading.pitch_deg
                )}
                °{"  "}

                YAW{" "}
                {format(
                  reading.yaw_deg
                )}
                °

              </div>


              {/* ENGINE HOTSPOTS */}

              <div className="engine-hotspots">

                <div
                  className={`
                    hotspot
                    ${
                      rangeStatus(
                        "cht_c",
                        reading.cht_c
                      )
                    }
                  `}
                >

                  <span />

                  CYLINDER HEAD

                </div>


                <div
                  className={`
                    hotspot
                    ${
                      rangeStatus(
                        "egt_c",
                        reading.egt_c
                      )
                    }
                  `}
                >

                  <span />

                  EXHAUST

                </div>


                <div
                  className={`
                    hotspot
                    ${
                      rangeStatus(
                        "oil_press_bar",
                        reading.oil_press_bar
                      )
                    }
                  `}
                >

                  <span />

                  OIL SYSTEM

                </div>


                <div
                  className={`
                    hotspot
                    ${
                      rangeStatus(
                        "injection_deg",
                        reading.injection_deg
                      )
                    }
                  `}
                >

                  <span />

                  INJECTOR

                </div>

              </div>

            </div>


            {/* ENGINE FOOTER */}

            <div className="twin-footer">

              <div className="twin-stat">

                <span>
                  RPM
                </span>

                <strong>
                  {format(
                    reading.rpm,
                    0
                  )}
                </strong>

              </div>


              <div className="twin-stat">

                <span>
                  CHT
                </span>

                <strong>
                  {format(
                    reading.cht_c
                  )}
                  °C
                </strong>

              </div>


              <div className="twin-stat">

                <span>
                  EGT
                </span>

                <strong>
                  {format(
                    reading.egt_c
                  )}
                  °C
                </strong>

              </div>


              <div className="twin-stat">

                <span>
                  VIB
                </span>

                <strong>
                  {format(
                    reading.vibration_g,
                    3
                  )}
                  G
                </strong>

              </div>


              <div className="twin-stat">

                <span>
                  OIL
                </span>

                <strong>
                  {format(
                    reading.oil_press_bar
                  )}
                  {" "}
                  BAR
                </strong>

              </div>

            </div>

          </div>


          {/* FAULT INJECTION */}

          <FaultInjection
            selectedFault={
              selectedFault
            }

            setSelectedFault={
              setSelectedFault
            }

            selectedProfile={
              selectedProfile
            }

            setSelectedProfile={
              setSelectedProfile
            }

            onInject={
              injectFault
            }

            onClear={
              clearFault
            }

            injecting={
              injecting
            }
          />

        </section>


        {/* ====================================================
            RIGHT COLUMN
            ==================================================== */}

        <section className="right-column">


          {/* FAULT STATUS */}

          <div
            className={`
              panel
              fault-status-panel
              ${
                activeFault !==
                "none"
                  ? "fault-status-active"
                  : ""
              }
            `}
          >

            <SectionHeader
              eyebrow="DIAGNOSTIC ENGINE"
              title="FAULT STATUS"
              right={

                <span
                  className={`
                    status-pill
                    ${
                      activeFault ===
                      "none"
                        ? "pill-green"
                        : "pill-red"
                    }
                  `}
                >

                  {activeFault ===
                  "none"
                    ? "CLEAR"
                    : "ACTIVE"}

                </span>

              }
            />


            <div className="fault-status-main">

              <div
                className={`
                  fault-status-icon
                  ${
                    activeFault ===
                    "none"
                      ? "icon-normal"
                      : "icon-fault"
                  }
                `}
              >

                {activeFault ===
                "none"
                  ? "✓"
                  : "!"}

              </div>


              <div>

                <strong>

                  {activeFault ===
                  "none"
                    ? "SYSTEM NOMINAL"
                    : prettyFault(
                        activeFault
                      )}

                </strong>


                <span>

                  {activeFault ===
                  "none"
                    ? "No active engine fault"
                    : activeFaultInfo.description}

                </span>

              </div>

            </div>


            {(() => {
              const rawFaults = [...(packet.possible_faults || [])];
              const aiPredicted = packet.ai?.predicted_fault;
              
              if (aiPredicted && aiPredicted !== "none") {
                const idx = rawFaults.indexOf(aiPredicted);
                if (idx > -1) {
                  rawFaults.splice(idx, 1);
                }
                rawFaults.unshift(aiPredicted);
              }

              const displayFaults = rawFaults.slice(0, 2);

              if (displayFaults.length === 0) return null;

              return (
                <div className="possible-faults">

                  <div className="mini-label">
                    POSSIBLE FAULT SIGNATURES (MAX 2)
                  </div>

                  {displayFaults.map((fault, index) => (

                    <div
                      className="possible-fault"
                      key={fault}
                    >

                      <i className="fault-icon">!</i>


                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
                        <span>
                          {fault.replaceAll("_", " ")}
                        </span>

                        {index === 0 && (
                          <span style={{
                            fontSize: '9px',
                            fontWeight: '800',
                            padding: '2px 6px',
                            borderRadius: '4px',
                            background: 'rgba(255, 170, 0, 0.25)',
                            border: '1px solid #ffaa00',
                            color: '#ffb84d',
                            textTransform: 'uppercase',
                            width: 'auto',
                            height: 'auto',
                            boxShadow: 'none'
                          }}>
                            MOST PROBABLE
                          </span>
                        )}
                      </div>

                    </div>

                  ))}

                </div>
              );
            })()}


          </div>


          {/* POWER */}

          <div className="panel">

            <SectionHeader
              eyebrow="ELECTRICAL SYSTEM"
              title="POWER & CHARGING"
            />


            <div className="electrical-display">

              <div className="battery-visual">

                <div className="battery-body">

                  <div
                    className="battery-fill"
                    style={{
                      width:
                        `${clamp(
                          normalize(
                            reading.battery_v,
                            11,
                            15
                          ) * 100,
                          0,
                          100
                        )}%`,
                    }}
                  />


                  <div className="battery-cells">

                    <i />
                    <i />
                    <i />
                    <i />

                  </div>

                </div>


                <div className="battery-terminal" />

              </div>


              <div className="battery-value">

                <strong>
                  {format(
                    reading.battery_v,
                    2
                  )}
                </strong>

                <span>
                  VOLTS
                </span>

              </div>

            </div>


            <div className="metric-list">

              <div>

                <span>
                  BATTERY STATUS
                </span>

                <strong
                  className={
                    rangeStatus(
                      "battery_v",
                      reading.battery_v
                    ) ===
                    "danger"
                      ? "text-danger"
                      : "text-green"
                  }
                >

                  {rangeStatus(
                    "battery_v",
                    reading.battery_v
                  ) ===
                  "danger"
                    ? "ABNORMAL"
                    : "NOMINAL"}

                </strong>

              </div>


              <div>

                <span>
                  SENSOR SOURCE
                </span>

                <SourceBadge
                  value={
                    source.battery_v
                  }
                />

              </div>

            </div>

          </div>


          {/* ATTITUDE */}

          <div className="panel attitude-panel">

            <SectionHeader
              eyebrow="FLIGHT DYNAMICS"
              title="ATTITUDE"
            />


            <div className="attitude-display">

              <div className="attitude-circle">

                <div
                  className="attitude-aircraft"
                  style={{
                    transform:
                      `
                        translate(
                          -50%,
                          -50%
                        )
                        rotate(
                          ${reading.roll_deg}deg
                        )
                      `,
                  }}
                >

                  <span />
                  <b />
                  <i />

                </div>


                <div className="attitude-crosshair">
                  +
                </div>

              </div>


              <div className="attitude-values">

                <div>

                  <span>
                    ROLL
                  </span>

                  <strong>
                    {format(
                      reading.roll_deg
                    )}
                    °
                  </strong>

                </div>


                <div>

                  <span>
                    PITCH
                  </span>

                  <strong>
                    {format(
                      reading.pitch_deg
                    )}
                    °
                  </strong>

                </div>


                <div>

                  <span>
                    YAW
                  </span>

                  <strong>
                    {format(
                      reading.yaw_deg
                    )}
                    °
                  </strong>

                </div>

              </div>

            </div>

          </div>


          {/* SENSOR SOURCES */}

          <div className="panel source-panel">

            <SectionHeader
              eyebrow="DATA FUSION"
              title="SENSOR SOURCES"
            />


            <div className="source-list">

              {[
                ["RPM", "rpm"],

                ["CHT", "cht_c"],

                ["EGT", "egt_c"],

                [
                  "OIL PRESS",
                  "oil_press_bar",
                ],

                [
                  "VIBRATION",
                  "vibration_g",
                ],

                [
                  "BATTERY",
                  "battery_v",
                ],

                [
                  "INJECTION",
                  "injection_deg",
                ],

              ].map(
                ([label, field]) => (

                  <div
                    className="source-row"
                    key={field}
                  >

                    <span>
                      {label}
                    </span>

                    <SourceBadge
                      value={
                        source[field]
                      }
                    />

                  </div>

                )
              )}

            </div>

          </div>

        </section>

      </main>


      {/* ======================================================
          BOTTOM STATUS BAR
          ====================================================== */}

      <footer className="bottom-status">

        <div className="bottom-left">

          <span className="status-light green" />

          AEROSYNX DIGITAL TWIN

          <span className="bottom-divider">
            |
          </span>

          ENGINE DT-01

        </div>


        <div className="bottom-center">

          <span>
            TELEMETRY:
          </span>

          <strong
            className={
              connected
                ? "text-green"
                : "text-danger"
            }
          >

            {connected
              ? "CONNECTED"
              : "DISCONNECTED"}

          </strong>

          <span>
            •
          </span>

          <span>
            UPDATE:
          </span>

          <strong>
            {updateText}
          </strong>

        </div>


        <div className="bottom-right">

          <span>
            PROFILE
          </span>

          <strong>
            {missionProfile
              .replaceAll(
                "_",
                " "
              )
              .toUpperCase()}
          </strong>

        </div>

      </footer>


      {/* ======================================================
          FULL SCREEN FAULT ALARM
          ====================================================== */}

      {alarmActive &&
        activeFault !==
          "none" && (

          <div className="alarm-overlay">

            <div className="alarm-content">

              <div className="alarm-symbol">
                !
              </div>

              <div>

                <strong>
                  ENGINE FAULT
                </strong>

                <span>
                  {prettyFault(
                    activeFault
                  )}
                </span>

              </div>

            </div>

          </div>

        )}


      {/* ======================================================
          REACT TOASTIFY CONTAINER
          ====================================================== */}

      <ToastContainer
        position="top-right"
        autoClose={3000}
        hideProgressBar={false}
        newestOnTop
        closeOnClick
        pauseOnFocusLoss
        draggable
        pauseOnHover
        theme="dark"
      />

    </div>
  );
}