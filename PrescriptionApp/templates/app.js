document.getElementById("uploadForm").onsubmit = async (event) => {
    event.preventDefault();

    const formData = new FormData(document.getElementById("uploadForm"));

    try {
        const response = await fetch("http://localhost:5000/upload", {
            method: "POST",
            body: formData
        });
        const result = await response.json();

        document.getElementById("purpose").textContent = result.purpose || "Not available";
        document.getElementById("keep_out_of_reach_of_children").textContent = result.keep_out_of_reach_of_children || "Not available";
        document.getElementById("warnings").textContent = result.warnings || "Not available";
        document.getElementById("dosage_and_administration").textContent = result.dosage_and_administration || "Not available";
        document.getElementById("pregnancy_or_breast_feeding").textContent = result.pregnancy_or_breast_feeding || "Not available";
        document.getElementById("stop_use").textContent = result.stop_use || "Not available";
    } catch (error) {
        console.error("Error fetching medicine information:", error);
    }
};
