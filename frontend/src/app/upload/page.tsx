"use client";
import Topbar from "@/components/Topbar";
import UploadForm from "@/components/UploadForm";

export default function UploadPage() {
  return (
    <>
      <Topbar title="Upload Video" />
      <main className="p-4 sm:p-6 space-y-4 min-w-0">
        <p className="text-slate-400 text-sm max-w-2xl">
          Upload a long video you own (podcast, interview, gaming), or paste a YouTube link to one.
          The pipeline analyses the full video and returns 3–5 strong clips — never a flood of random cuts.
        </p>
        <UploadForm />
      </main>
    </>
  );
}
