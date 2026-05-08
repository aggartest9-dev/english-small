import { Link } from "react-router-dom";

export default function Dashboard() {
  return (
    <div>
      <h2>Select Session</h2>

      <Link to="/session/beginner/1">Beginner Day 1</Link>
    </div>
  );
}