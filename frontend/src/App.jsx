import { useState } from "react";

function App() {
  const [showLogin, setShowLogin] = useState(true);

  const [isLoggedIn, setIsLoggedIn] = useState(
    Boolean(localStorage.getItem("access_token"))
  );

  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [message, setMessage] = useState("");

  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadMessage, setUploadMessage] = useState("");

  const [showJobAnalysis, setShowJobAnalysis] = useState(false);
  const [jobDescription, setJobDescription] = useState("");
  const [analysisMessage, setAnalysisMessage] = useState("");
  const [analysisResult, setAnalysisResult] = useState(null);
  const [showResults, setShowResults] = useState(false);
const [savedAnalyses, setSavedAnalyses] = useState([]);
const [resultsMessage, setResultsMessage] = useState("");

  const storedUser = localStorage.getItem("user");

  const [user, setUser] = useState(
    storedUser ? JSON.parse(storedUser) : null
  );

  // =====================================================
  // LOGIN
  // =====================================================

  async function handleLogin(event) {
    event.preventDefault();

    setMessage("Logging in...");

    try {
      const url =
        `http://127.0.0.1:8000/login` +
        `?email=${encodeURIComponent(loginEmail)}` +
        `&password=${encodeURIComponent(loginPassword)}`;

      const response = await fetch(url, {
        method: "POST",
        headers: {
          Accept: "application/json",
        },
      });

      const data = await response.json();

      if (!response.ok) {
        const errorMessage =
          typeof data.detail === "string"
            ? data.detail
            : "Invalid email or password.";

        setMessage(errorMessage);
        return;
      }

      localStorage.setItem(
        "access_token",
        data.access_token
      );

      const loggedInUser = {
        id: data.id,
        name: data.name,
        email: data.email,
      };

      localStorage.setItem(
        "user",
        JSON.stringify(loggedInUser)
      );

      setUser(loggedInUser);
      setIsLoggedIn(true);
      setMessage("");
    } catch (error) {
      console.error("Login error:", error);

      setMessage(
        "Could not connect to CareerLens backend."
      );
    }
  }

  // =====================================================
  // UPLOAD RESUME
  // =====================================================

  async function handleUpload(fileToUpload = selectedFile) {
    if (!fileToUpload) {
      setUploadMessage(
        "Please choose a PDF first."
      );
      return;
    }

    if (fileToUpload.type !== "application/pdf") {
      setUploadMessage(
        "Please select a PDF file."
      );
      return;
    }

    const token = localStorage.getItem(
      "access_token"
    );

    if (!token) {
      setUploadMessage(
        "Please login again."
      );
      return;
    }

    const formData = new FormData();

    formData.append(
      "file",
      fileToUpload
    );

    setUploadMessage(
      "Uploading resume..."
    );

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/upload-resume",
        {
          method: "POST",

          headers: {
            Authorization: `Bearer ${token}`,
            Accept: "application/json",
          },

          body: formData,
        }
      );

      const data = await response.json();

      if (!response.ok) {
        let errorMessage =
          "Resume upload failed.";

        if (typeof data.detail === "string") {
          errorMessage = data.detail;
        } else if (Array.isArray(data.detail)) {
          errorMessage = data.detail
            .map((error) =>
              typeof error === "string"
                ? error
                : error?.msg || JSON.stringify(error)
            )
            .join(", ");
        }

        setUploadMessage(errorMessage);
        return;
      }

      setUploadMessage(
        `Resume uploaded successfully! Found ${
          data.skills?.length || 0
        } skills.`
      );

      setSelectedFile(null);
    } catch (error) {
      console.error(
        "Upload error:",
        error
      );

      setUploadMessage(
        "Could not connect to CareerLens backend."
      );
    }
  }

  // =====================================================
  // FILE SELECTION
  // =====================================================

  function handleFileSelect(event) {
    const file = event.target.files?.[0];

    if (!file) {
      return;
    }

    setSelectedFile(file);
    setUploadMessage("");

    handleUpload(file);

    event.target.value = "";
  }

  // =====================================================
  // ANALYZE CUSTOM JOB
  // =====================================================

  async function handleAnalyzeJob() {
    if (!jobDescription.trim()) {
      setAnalysisMessage(
        "Please paste a job description first."
      );
      return;
    }

    const token = localStorage.getItem(
      "access_token"
    );

    if (!token) {
      setAnalysisMessage(
        "Please login again."
      );
      return;
    }

    setAnalysisMessage(
      "Analyzing your resume..."
    );

    setAnalysisResult(null);

    try {
      // ==========================================
      // GET USER'S RESUMES
      // ==========================================

      const resumeResponse = await fetch(
        "http://127.0.0.1:8000/resumes",
        {
          method: "GET",

          headers: {
            Authorization: `Bearer ${token}`,
            Accept: "application/json",
          },
        }
      );

      const resumesData =
        await resumeResponse.json();

      if (!resumeResponse.ok) {
        let errorMessage =
          "Could not load your resumes.";

        if (typeof resumesData.detail === "string") {
          errorMessage = resumesData.detail;
        } else if (
          Array.isArray(resumesData.detail)
        ) {
          errorMessage = resumesData.detail
            .map((error) =>
              typeof error === "string"
                ? error
                : error?.msg || JSON.stringify(error)
            )
            .join(", ");
        }

        setAnalysisMessage(errorMessage);
        return;
      }

      // ==========================================
      // HANDLE RESUME RESPONSE
      // ==========================================

      const resumes = Array.isArray(resumesData)
        ? resumesData
        : resumesData.resumes || [];

      if (!resumes.length) {
        setAnalysisMessage(
          "Please upload a resume first."
        );
        return;
      }

      // Use newest resume
      const latestResume =
        resumes[resumes.length - 1];

      // ==========================================
      // ANALYZE CUSTOM JOB
      // ==========================================

      const url =
        `http://127.0.0.1:8000/analyze-custom-job` +
        `?resume_id=${encodeURIComponent(
          latestResume.id
        )}` +
        `&job_description=${encodeURIComponent(
          jobDescription
        )}`;

      const response = await fetch(url, {
        method: "POST",

        headers: {
          Authorization: `Bearer ${token}`,
          Accept: "application/json",
        },
      });

      const data = await response.json();

      // ==========================================
      // HANDLE BACKEND ERROR
      // ==========================================

      if (!response.ok) {
        let errorMessage =
          "Analysis failed.";

        if (typeof data.detail === "string") {
          errorMessage = data.detail;
        } else if (Array.isArray(data.detail)) {
          errorMessage = data.detail
            .map((error) => {
              if (typeof error === "string") {
                return error;
              }

              if (error?.msg) {
                return error.msg;
              }

              return JSON.stringify(error);
            })
            .join(", ");
        } else if (data.detail) {
          errorMessage = JSON.stringify(
            data.detail
          );
        }

        setAnalysisMessage(errorMessage);
        return;
      }

      // ==========================================
      // SUCCESS
      // ==========================================

      setAnalysisResult(data);

      setAnalysisMessage(
        "Analysis complete!"
      );
    } catch (error) {
      console.error(
        "Analysis error:",
        error
      );

      setAnalysisMessage(
        "Could not connect to CareerLens backend."
      );
    }
  }

  // =====================================================
  // LOGOUT
  // =====================================================
// =====================================================
// VIEW SAVED RESULTS
// =====================================================

async function handleViewResults() {
  const token = localStorage.getItem("access_token");

  if (!token) {
    setResultsMessage("Please login again.");
    return;
  }

  setResultsMessage("Loading your results...");
  setShowResults(true);

  try {
    const response = await fetch(
      "http://127.0.0.1:8000/analyses",
      {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: "application/json",
        },
      }
    );

    const data = await response.json();

    if (!response.ok) {
      const errorMessage =
        typeof data.detail === "string"
          ? data.detail
          : "Could not load your results.";

      setResultsMessage(errorMessage);
      return;
    }

    const analyses = Array.isArray(data)
  ? data
  : data.analyses || [];

const latestAnalysis = analyses.length > 0
  ? analyses[0]
  : null;

setSavedAnalyses(
  latestAnalysis ? [latestAnalysis] : []
);

    if (analyses.length === 0) {
      setResultsMessage(
        "No saved analyses yet. Analyze a job first."
      );
    } else {
      setResultsMessage("");
    }
  } catch (error) {
    console.error("Results error:", error);

    setResultsMessage(
      "Could not connect to CareerLens backend."
    );
  }
}
  function handleLogout() {
    localStorage.removeItem(
      "access_token"
    );

    localStorage.removeItem(
      "user"
    );

    setUser(null);
    setIsLoggedIn(false);
    setShowLogin(true);

    setLoginEmail("");
    setLoginPassword("");
    setMessage("");

    setSelectedFile(null);
    setUploadMessage("");

    setShowJobAnalysis(false);
    setJobDescription("");
    setAnalysisMessage("");
    setAnalysisResult(null);
  }

  // =====================================================
  // DASHBOARD
  // =====================================================

  if (isLoggedIn) {
    return (
      <div className="app">
        <div className="card">

          <h1>CareerLens</h1>

          <p className="subtitle">
            Your career dashboard
          </p>

          <h2>
            Welcome, {user?.name}! 👋
          </h2>

          <p>
            Upload your resume and discover
            your career match.
          </p>

          {/* =====================================
              UPLOAD RESUME
          ====================================== */}

          <div className="dashboard-button">
            <input
              id="resume-file"
              type="file"
              accept=".pdf,application/pdf"
              style={{ display: "none" }}
              onChange={handleFileSelect}
            />

            <button
              onClick={() => {
                document
                  .getElementById("resume-file")
                  .click();
              }}
            >
              📄 Upload Resume
            </button>

            {uploadMessage && (
              <p className="status-message">
                {uploadMessage}
              </p>
            )}
          </div>

          {/* =====================================
              ANALYZE JOB BUTTON
          ====================================== */}

          <div className="dashboard-button">
            <button
              onClick={() => {
                setShowJobAnalysis(true);
                setAnalysisMessage("");
                setAnalysisResult(null);
              }}
            >
              🎯 Analyze a Job
            </button>
          </div>

          {/* =====================================
              JOB ANALYSIS SECTION
          ====================================== */}

          {showJobAnalysis && (
            <div className="analysis-section">

              <h3>
  What job are you looking for?
</h3>

              <input
  type="text"
  className="job-role-input"
  placeholder="e.g. Python Developer"
  value={jobDescription}
  onChange={(event) =>
    setJobDescription(
      event.target.value
    )
  }
/>

              <button
                className="analyze-button"
                onClick={handleAnalyzeJob}
              >
                Analyze Resume
              </button>

              {analysisMessage && (
                <p className="status-message">
                  {analysisMessage}
                </p>
              )}

              {/* =================================
                  ANALYSIS RESULTS
              ================================== */}

              {analysisResult && (
                <div className="results-box">

                  <h2>
                    {analysisResult.match_percentage}%
                    Match
                  </h2>

                  <h3>
                    Matched Skills
                  </h3>

                  {Array.isArray(
                    analysisResult.matched_skills
                  ) &&
                  analysisResult.matched_skills.length >
                    0 ? (
                    <ul>
                      {analysisResult.matched_skills.map(
                        (skill, index) => (
                          <li key={index}>
                            {skill}
                          </li>
                        )
                      )}
                    </ul>
                  ) : (
                    <p>
                      No matching skills found.
                    </p>
                  )}

                  <h3>
                    Missing Skills
                  </h3>

                  {Array.isArray(
                    analysisResult.missing_skills
                  ) &&
                  analysisResult.missing_skills.length >
                    0 ? (
                    <ul>
                      {analysisResult.missing_skills.map(
                        (skill, index) => (
                          <li key={index}>
                            {skill}
                          </li>
                        )
                      )}
                    </ul>
                  ) : (
                    <p>
                      No missing skills 🎉
                    </p>
                  )}

                  <h3>
                    Recommendations
                  </h3>

                  {Array.isArray(
                    analysisResult.recommendations
                  ) &&
                  analysisResult.recommendations.length >
                    0 ? (
                    <ul>
                      {analysisResult.recommendations.map(
                        (
                          recommendation,
                          index
                        ) => (
                          <li key={index}>
                            {recommendation}
                          </li>
                        )
                      )}
                    </ul>
                  ) : (
                    <p>
                      Your skills match the
                      job requirements well!
                    </p>
                  )}

                </div>
              )}

            </div>
          )}

          {/* =====================================
              VIEW RESULTS
          ====================================== */}

          <div className="dashboard-button results-button">
            <button onClick={handleViewResults}>
  📊 View Results
</button>
{showResults && (
  <div className="saved-results">

    <h2>My Results</h2>

    {resultsMessage && (
      <p className="status-message">
        {resultsMessage}
      </p>
    )}

    {savedAnalyses.map((analysis) => (
      <div
        className="saved-result-card"
        key={analysis.id}
      >
        <h3>
          {analysis.job_title}
        </h3>

        <div className="match-score">
          {analysis.match_percentage}%
        </div>

        <p>
          <strong>Matched Skills:</strong>
        </p>

        <p>
          {analysis.matched_skills ||
            "None"}
        </p>

        <p>
          <strong>Missing Skills:</strong>
        </p>

        <p>
          {analysis.missing_skills ||
            "None"}
        </p>

        <p>
          <strong>Recommendations:</strong>
        </p>

        <p>
          {analysis.recommendations ||
            "None"}
        </p>
      </div>
    ))}

  </div>
)}
          </div>

          {/* =====================================
              LOGOUT
          ====================================== */}

          <div className="dashboard-button logout-button">
            <button
              onClick={handleLogout}
            >
              Logout
            </button>
          </div>

        </div>
      </div>
    );
  }

  // =====================================================
  // LOGIN / REGISTER
  // =====================================================

  return (
    <div className="app">
      <div className="card">

        <h1>CareerLens</h1>

        <p className="subtitle">
          Find your career match
        </p>

        {showLogin ? (
          <>
            <h2>
              Welcome back
            </h2>

            <form
              onSubmit={handleLogin}
            >

              <input
                type="email"
                placeholder="Email"
                value={loginEmail}
                onChange={(event) =>
                  setLoginEmail(
                    event.target.value
                  )
                }
                required
              />

              <input
                type="password"
                placeholder="Password"
                value={loginPassword}
                onChange={(event) =>
                  setLoginPassword(
                    event.target.value
                  )
                }
                required
              />

              <button
                type="submit"
              >
                Login
              </button>

            </form>

            {message && (
              <p className="status-message">
                {message}
              </p>
            )}

            <p>
              Don't have an account?{" "}

              <span
                onClick={() => {
                  setShowLogin(false);
                  setMessage("");
                }}
                className="link"
              >
                Register
              </span>
            </p>
          </>
        ) : (
          <>
            <h2>
              Create account
            </h2>

            <input
              type="text"
              placeholder="Name"
            />

            <input
              type="email"
              placeholder="Email"
            />

            <input
              type="password"
              placeholder="Password"
            />

            <button>
              Register
            </button>

            <p>
              Already have an account?{" "}

              <span
                onClick={() => {
                  setShowLogin(true);
                  setMessage("");
                }}
                className="link"
              >
                Login
              </span>
            </p>
          </>
        )}

      </div>
    </div>
  );
}

export default App;