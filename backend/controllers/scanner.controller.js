import axios from "axios";

{/*export const runScanner = async (req, res) => {
  try {
    const response = await axios.get("http://127.0.0.1:5000/scan");
    // Send Flask data directly
    return res.json(response.data);
  } catch (error) {
    console.error("Scanner Error:", error.message);
    return res.status(500).json({ success: false, message: "Python scanner not running" });
  }
};*/}

export const runScanner = async (req, res) => {
  try {
    // ✅ Get conditions from frontend (support GET query or POST body)
    let conditions = req.body?.conditions || req.query?.conditions || [];

    if (typeof conditions === "string") {
      try {
        conditions = JSON.parse(conditions);
      } catch (err) {
        conditions = [];
      }
    }

    console.log("Received from frontend:", conditions);

    // ✅ Send to Flask
   {/*} await axios.post("http://127.0.0.1:5000/scan/", {
      conditions
    });*/}
    /*await axios.post("http://127.0.0.1:5000/scan/start", {
  conditions
}*/
    const scannerBaseUrl =
      (process.env.SCAN_SERVICE_URL || "http://localhost:5000").replace(/\/+$/, "");

    const response = await axios.get(
      `${scannerBaseUrl}/scan?conditions=${encodeURIComponent(JSON.stringify(conditions))}`
    );



    return res.json({
      success: true,
      message: "Scan started"
    });

  } catch (error) {
    console.error("Scanner Error:", error.message);

    return res.status(500).json({
      success: false,
      message: "Python scanner not running"
    });
  }
};