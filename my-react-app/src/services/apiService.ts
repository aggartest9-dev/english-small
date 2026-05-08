export const apiService = {
  getSession: async (level: string, day: number) => {
    const res = await fetch(
      `http://127.0.0.1:8000/api/sessions/?level=${level}&day=${day}`
    );

    if (!res.ok) {
      throw new Error("Failed to load session");
    }

    return res.json();
  }
};