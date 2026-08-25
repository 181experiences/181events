// POST /signout -> clears the session cookie and returns to the calendar.
import { sessionCookie, seeOther } from "./_resident.js";

export async function onRequestPost() {
  return seeOther("/", sessionCookie(""));
}

export async function onRequestGet() {
  return seeOther("/");
}
