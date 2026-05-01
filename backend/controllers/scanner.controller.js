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
    // ✅ Get conditions from frontend
    const { conditions } = req.body;

    console.log("Received from frontend:", conditions);

    // ✅ Send to Flask
   {/*} await axios.post("http://127.0.0.1:5000/scan/", {
      conditions
    });*/}
    /*await axios.post("http://127.0.0.1:5000/scan/start", {
  conditions
}*/
const response = await axios.get(
  `http://localhost:5000/scan?conditions=${encodeURIComponent(JSON.stringify(conditions))}`
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