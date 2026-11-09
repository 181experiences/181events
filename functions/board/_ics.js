// iCalendar rendering for Board meetings, shared by the feed and the single-
// meeting download. Times are floating local, matching the event files the
// static calendar ships.

import { to24, icsStamp } from "../_lib.js";

export function icsEvent(ev) {
  const d = ev.date.replace(/-/g, "");
  const start = ev.start24 || to24(ev.start);
  const end = ev.end_time ? to24(ev.end_time) : start;
  const title = String(ev.title || "Board Meeting").replace(/[\r\n,;]/g, " ");
  const loc = String(ev.location || "Level 39").replace(/[\r\n,;]/g, " ");
  const { seq, stamp } = icsStamp();
  return [
    "BEGIN:VEVENT",
    `UID:181fremont-board-${ev.id}@181residents.com`,
    `DTSTAMP:${stamp}`, `SEQUENCE:${seq}`,
    `DTSTART:${d}T${start}00`,
    `DTEND:${d}T${end}00`,
    `SUMMARY:${title}`,
    `LOCATION:181 Fremont - ${loc}`,
    "END:VEVENT",
  ].join("\r\n") + "\r\n";
}

// A meeting taken off the Board calendar says so under its own UID, so a
// subscriber's copy is withdrawn rather than left to linger.
export function icsCancelled(ev) {
  const d = ev.date.replace(/-/g, "");
  const start = ev.start24 || to24(ev.start) || "0000";
  const title = String(ev.title || "Board Meeting").replace(/[\r\n,;]/g, " ");
  const { seq, stamp } = icsStamp();
  return [
    "BEGIN:VEVENT",
    `UID:181fremont-board-${ev.id}@181residents.com`,
    `DTSTAMP:${stamp}`, `SEQUENCE:${seq + 1000}`,
    "STATUS:CANCELLED",
    `DTSTART:${d}T${start}00`,
    `DTEND:${d}T${start}00`,
    `SUMMARY:Cancelled: ${title}`,
    "END:VEVENT",
  ].join("\r\n") + "\r\n";
}

export function plainIcs(eventsBlock, name) {
  return [
    "BEGIN:VCALENDAR", "VERSION:2.0",
    "PRODID:-//181 Fremont//Board Meetings//EN",
    `X-WR-CALNAME:${name}`,
  ].join("\r\n") + "\r\n" + eventsBlock + "END:VCALENDAR\r\n";
}
