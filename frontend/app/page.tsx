import Image from "next/image";
import Link from "next/link";

import { API_BASE_URL } from "@/lib/api-client";

const SECTIONS = [
  {
    href: "/schemes",
    title: "Course schemes",
    description:
      "Upload a program's scheme document, check the text read from it, confirm the course rows and keep every scheme year on record.",
  },
  {
    href: "/dashboard",
    title: "Stats overview",
    description: "Counts of departments, programs, saved schemes and courses, read straight from the database.",
  },
];

export default function HomePage() {
  // Landing page: what the system is, and the two sections that work today.
  return (
    <main className="mx-auto w-full max-w-5xl px-4 py-10 sm:px-6 sm:py-16">
      <section className="flex flex-col items-center text-center">
        <Image
          src="/imcs-logo.png"
          alt="Institute of Mathematics & Computer Science, University of Sindh"
          width={140}
          height={140}
          priority
        />
        <h1 className="mt-6 text-3xl font-semibold text-content sm:text-4xl">IMCS Scheduler</h1>
        <p className="mt-3 max-w-2xl text-content/70">
          Timetable generation and academic scheduling for the Institute of Mathematics &amp; Computer Science,
          University of Sindh.
        </p>
      </section>

      <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2">
        {SECTIONS.map((section) => (
          <Link
            key={section.href}
            href={section.href}
            className="rounded-xl bg-card p-6 shadow-sm ring-1 ring-content/10 transition hover:ring-primary/50"
          >
            <h2 className="text-lg font-semibold text-content">{section.title}</h2>
            <p className="mt-2 text-sm text-content/70">{section.description}</p>
            <span className="mt-4 inline-block text-sm font-medium text-primary">Open {section.title.toLowerCase()} →</span>
          </Link>
        ))}
      </div>

      <p className="mt-10 break-all text-center text-xs text-content/50">
        API reference:{" "}
        <a href={`${API_BASE_URL}/docs`} className="underline hover:text-content">
          {API_BASE_URL}/docs
        </a>
      </p>
    </main>
  );
}
