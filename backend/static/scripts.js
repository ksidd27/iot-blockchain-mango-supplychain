document.addEventListener("DOMContentLoaded", () => {
  const createForm = document.getElementById("createForm");
  const updateForm = document.getElementById("updateForm");
  const refreshBtn = document.getElementById("refreshBtn");

  if (!createForm || !updateForm || !refreshBtn) {
    console.error("❌ Some HTML elements not found!");
    return;
  }

  const apiBase = "http://127.0.0.1:5000";

  // --- Create batch ---
  createForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const origin = document.getElementById("origin").value;
    const farm = document.getElementById("farm").value;
    const exporter = document.getElementById("exporter").value;
    const ipfsHash = document.getElementById("ipfsHash").value;

    const res = await fetch(`${apiBase}/create_batch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ origin, farm, exporter, ipfsHash }),
    });

    const data = await res.json();
    document.getElementById("createMsg").innerText = data.message || data.error;
    loadBatches();
  });

  // --- Update status ---
  updateForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("batchId").value;
    const status = document.getElementById("newstatus").value;
    const ipfsHash = document.getElementById("ipfsHashUpdate").value;
    const color = document.getElementById("color").value;
    const temperature = document.getElementById("temperature").value;

    const res = await fetch(`${apiBase}/update_status`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id, status, ipfsHash, color, temperature }),
    });
    const data = await res.json();
    document.getElementById("updateMsg").innerText = data.message || data.error;
    loadBatches();
  });

  // --- Load batches ---
  async function loadBatches() {
    const res = await fetch(`${apiBase}/local_batches`);
    const data = await res.json();
    const list = document.getElementById("batchList");
    list.innerHTML = "";
    if (!data.batches || !data.batches.length) {
      list.innerHTML = "<p>No batches found.</p>";
      return;
    }
    data.batches.forEach((b) => {
      const div = document.createElement("div");
      div.className = "batch";
      div.innerHTML = `
        <strong>ID:</strong> ${b.id}<br>
        <strong>Origin:</strong> ${b.origin}<br>
        <strong>Exporter:</strong> ${b.exporter}<br>
        <strong>Status:</strong> ${b.status}<br>
        <strong>IPFS:</strong> ${b.ipfsHash}<br>
        <strong>Color:</strong> ${b.color}<br>
        <strong>Temperature:</strong> ${b.temperature}<br>
        <strong>Tx:</strong> ${b.tx_hash}<br>
        <small>${b.timestamp}</small>
      `;
      list.appendChild(div);
    });
  }

  // --- Refresh button ---
  refreshBtn.addEventListener("click", loadBatches);

  // Initial load
  loadBatches();
});
