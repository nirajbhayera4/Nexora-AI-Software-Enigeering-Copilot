
import {
  SearchCode,
  Network,
  Bug,
  FileText,
  Database,
  MessageSquareText,
} from 'lucide-react';

const features = [
  {
    icon: SearchCode,
    title: 'GitHub repository connection',
    description:
      'Connect a public GitHub repository, inspect its details, and index its source code.',
    status: 'Available',
  },
  {
    icon: Database,
    title: 'Code indexing and search',
    description:
      'Retrieve relevant code from an indexed repository to ground answers in your source.',
    status: 'Available',
  },
  {
    icon: MessageSquareText,
    title: 'Repository Q&A',
    description:
      'Ask questions in natural language and see answers with the source files and lines used.',
    status: 'Available',
  },
  {
    icon: Bug,
    title: 'AI code review',
    description:
      'Review prioritized source files for potential bugs, logic issues, and code quality improvements.',
    status: 'Available',
  },
  {
    icon: Network,
    title: 'Architecture analysis',
    description:
      'Explore project structure, modules, dependencies, circular imports, and UML diagrams.',
    status: 'Available',
  },
  {
    icon: FileText,
    title: 'Code documentation',
    description:
      'Generate standalone documentation for repositories and code modules.',
    status: 'Planned',
  },
];

function Features() {
  return (
    <section id="features" className="bg-[#f6faf9] px-6 py-24 lg:px-10">
      <div className="mx-auto max-w-7xl">

        <div className="max-w-2xl">
          <span className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-600">
            Available features
          </span>

          <h2 className="mt-4 text-3xl font-semibold tracking-tight text-slate-900 sm:text-5xl">
            Explore, review, and
            <span className="text-blue-600"> understand your code.</span>
          </h2>

          <p className="mt-5 leading-7 text-slate-500">
            Connect and index a public GitHub repository, ask source-grounded questions,
            review code, and inspect its architecture.
          </p>
        </div>

        <div className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((feature) => {
            const Icon = feature.icon;

            return (
              <div
                key={feature.title}
                className="rounded-2xl border border-slate-200 bg-white p-7 transition duration-300 hover:-translate-y-1 hover:border-blue-200 hover:shadow-lg hover:shadow-slate-900/5"
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
                  <Icon size={23} />
                </div>

                <div className="mt-6 flex flex-wrap items-center justify-between gap-2">
                  <h3 className="text-lg font-semibold text-slate-900">
                    {feature.title}
                  </h3>

                  <span className={`rounded-full px-2.5 py-1 text-[10px] font-medium ${
                    feature.status === 'Available'
                      ? 'bg-emerald-50 text-emerald-700'
                      : 'bg-slate-100 text-slate-500'
                  }`}>
                    {feature.status}
                  </span>
                </div>

                <p className="mt-3 text-sm leading-7 text-slate-500">
                  {feature.description}
                </p>
              </div>
            );
          })}
        </div>

      </div>
    </section>
  );
}

export default Features;
