import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";
// import { StagewiseToolbar } from "@stagewise/toolbar-react";
// import ReactPlugin from "@stagewise-plugins/react";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    {/* <StagewiseToolbar config={{ plugins: [ReactPlugin] }} /> */}
    <App />
  </React.StrictMode>
);
