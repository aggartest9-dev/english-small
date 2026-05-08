import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import client from "../api/client";

export default function SessionPage() {
  const { level, day } = useParams();

  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);

  const [answers, setAnswers] = useState({});
  const [recordingAudioId, setRecordingAudioId] =
    useState(null);
  const [recordingVideoId, setRecordingVideoId] =
    useState(null);

  const mediaRecorderRef = useRef(null);
  const previewVideoRef = useRef(null);
  const streamRef = useRef(null);
  const chunksRef = useRef([]);

  useEffect(() => {
    async function fetchSession() {
      try {
        const res = await client.get(
          `/sessions/?level=${level}&day=${day}`
        );
        setSession(res.data);
      } catch (error) {
        console.log(error);
      } finally {
        setLoading(false);
      }
    }

    fetchSession();
  }, [level, day]);

  function getEmbedUrl(url) {
    if (!url) return "";

    if (url.includes("watch?v=")) {
      const id = url
        .split("watch?v=")[1]
        .split("&")[0];

      return `https://www.youtube.com/embed/${id}`;
    }

    if (url.includes("youtu.be/")) {
      const id = url.split("youtu.be/")[1];
      return `https://www.youtube.com/embed/${id}`;
    }

    return url;
  }

  function saveAnswer(questionId, data) {
    setAnswers((prev) => ({
      ...prev,
      [questionId]: {
        ...prev[questionId],
        ...data,
      },
    }));
  }

  function handleOption(questionId, optionId) {
    saveAnswer(questionId, {
      selected_option: optionId,
    });
  }

  function handleText(questionId, value) {
    saveAnswer(questionId, {
      text_answer: value,
    });
  }

  function handleAudioUpload(questionId, file) {
    saveAnswer(questionId, {
      audio_file: file,
    });
  }

  function handleVideoUpload(questionId, file) {
    saveAnswer(questionId, {
      video_file: file,
    });
  }

  async function startAudioRecording(questionId) {
    try {
      const stream =
        await navigator.mediaDevices.getUserMedia(
          {
            audio: true,
          }
        );

      streamRef.current = stream;

      const recorder =
        new MediaRecorder(stream);

      mediaRecorderRef.current = recorder;
      chunksRef.current = [];

      setRecordingAudioId(questionId);

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      recorder.onstop = () => {
        const blob = new Blob(
          chunksRef.current,
          {
            type: "audio/webm",
          }
        );

        const file = new File(
          [blob],
          `audio-${questionId}.webm`,
          {
            type: "audio/webm",
          }
        );

        saveAnswer(questionId, {
          audio_file: file,
        });

        stopTracks();
        setRecordingAudioId(null);
      };

      recorder.start();
    } catch (error) {
      alert(
        "Microphone permission denied or unavailable."
      );
      console.log(error);
    }
  }

  function stopAudioRecording() {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
    }
  }

  async function startVideoRecording(questionId) {
    try {
      const stream =
        await navigator.mediaDevices.getUserMedia(
          {
            video: true,
            audio: true,
          }
        );

      streamRef.current = stream;

      if (previewVideoRef.current) {
        previewVideoRef.current.srcObject =
          stream;
      }

      const recorder =
        new MediaRecorder(stream);

      mediaRecorderRef.current = recorder;
      chunksRef.current = [];

      setRecordingVideoId(questionId);

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      recorder.onstop = () => {
        const blob = new Blob(
          chunksRef.current,
          {
            type: "video/webm",
          }
        );

        const file = new File(
          [blob],
          `video-${questionId}.webm`,
          {
            type: "video/webm",
          }
        );

        saveAnswer(questionId, {
          video_file: file,
        });

        if (previewVideoRef.current) {
          previewVideoRef.current.srcObject =
            null;
        }

        stopTracks();
        setRecordingVideoId(null);
      };

      recorder.start();
    } catch (error) {
      alert(
        "Camera/Microphone permission denied."
      );
      console.log(error);
    }
  }

  function stopVideoRecording() {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
    }
  }

  function stopTracks() {
    if (streamRef.current) {
      streamRef.current
        .getTracks()
        .forEach((track) =>
          track.stop()
        );
    }
  }

  function handleSubmit() {
    console.log("Answers:", answers);

    alert(
      "Answers collected successfully. Next step: send to backend."
    );
  }

  if (loading) return <h2>Loading...</h2>;

  if (!session) return <h2>No session found.</h2>;

  return (
    <div
      style={{
        maxWidth: "900px",
        margin: "auto",
        padding: "20px",
      }}
    >
      <h1>{session.title}</h1>

      <p>{session.description}</p>

      <h3>
        {session.level} | Day {session.day}
      </h3>

      {session.video_url && (
        <div
          style={{
            marginBottom: "30px",
          }}
        >
          <iframe
            width="100%"
            height="420"
            src={getEmbedUrl(
              session.video_url
            )}
            title="Lesson Video"
            allowFullScreen
          ></iframe>
        </div>
      )}

      <h2>Questions</h2>

      {session.questions.map(
        (q, index) => (
          <div
            key={q.id}
            style={{
              border:
                "1px solid #ddd",
              padding: "20px",
              borderRadius: "10px",
              marginBottom: "20px",
            }}
          >
            <h4>
              {index + 1}. {q.text}
            </h4>

            <p>
              <small>
                Type:{" "}
                {
                  q.response_type
                }
              </small>
            </p>

            {/* MCQ */}
            {q.response_type ===
              "option" &&
              q.options.map(
                (opt) => (
                  <div
                    key={
                      opt.id
                    }
                  >
                    <label>
                      <input
                        type="radio"
                        name={`q-${q.id}`}
                        onChange={() =>
                          handleOption(
                            q.id,
                            opt.id
                          )
                        }
                      />{" "}
                      {
                        opt.text
                      }
                    </label>
                  </div>
                )
              )}

            {/* TEXT */}
            {q.response_type ===
              "text" && (
              <input
                type="text"
                placeholder="Type answer"
                style={{
                  width:
                    "100%",
                  padding:
                    "10px",
                }}
                onChange={(
                  e
                ) =>
                  handleText(
                    q.id,
                    e.target
                      .value
                  )
                }
              />
            )}

            {/* AUDIO */}
            {q.response_type ===
              "audio" && (
              <div>
                <p>
                  Upload
                  Audio:
                </p>

                <input
                  type="file"
                  accept="audio/*"
                  onChange={(
                    e
                  ) =>
                    handleAudioUpload(
                      q.id,
                      e
                        .target
                        .files[0]
                    )
                  }
                />

                <p>
                  OR
                </p>

                {recordingAudioId ===
                q.id ? (
                  <button
                    onClick={
                      stopAudioRecording
                    }
                  >
                    Stop
                    Recording
                  </button>
                ) : (
                  <button
                    onClick={() =>
                      startAudioRecording(
                        q.id
                      )
                    }
                  >
                    Record
                    Audio
                  </button>
                )}
              </div>
            )}

            {/* VIDEO */}
            {q.response_type ===
              "video" && (
              <div>
                <p>
                  Upload
                  Video:
                </p>

                <input
                  type="file"
                  accept="video/*"
                  onChange={(
                    e
                  ) =>
                    handleVideoUpload(
                      q.id,
                      e
                        .target
                        .files[0]
                    )
                  }
                />

                <p>
                  OR
                </p>

                {recordingVideoId ===
                q.id ? (
                  <>
                    <video
                      ref={
                        previewVideoRef
                      }
                      autoPlay
                      muted
                      width="320"
                    />

                    <br />

                    <button
                      onClick={
                        stopVideoRecording
                      }
                    >
                      Stop
                      Recording
                    </button>
                  </>
                ) : (
                  <button
                    onClick={() =>
                      startVideoRecording(
                        q.id
                      )
                    }
                  >
                    Record
                    Video
                  </button>
                )}
              </div>
            )}
          </div>
        )
      )}

      <button
        onClick={handleSubmit}
        style={{
          padding:
            "12px 25px",
          fontSize:
            "16px",
          cursor:
            "pointer",
        }}
      >
        Submit Answers
      </button>
    </div>
  );
}