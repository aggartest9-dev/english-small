import { Link } from "react-router-dom";

export default function Home() {
  return (
    <div>
      <h1>English Learning Platform</h1>
      <Link to="/dashboard">Enter App</Link>
    </div>
  );
}