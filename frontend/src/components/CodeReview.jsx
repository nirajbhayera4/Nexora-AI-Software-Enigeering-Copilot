import { useState } from 'react';
import axios from 'axios';

const categories = {
    bug: 'Potential bug',
    logic: 'Logical error',
    quality: 'Code quality',
    optimization: 'Optimization',
};

export default function CodeReview({ repositoryUrl }) {
    const [review, setReview] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    async function runReview() {
        setLoading(true);
        setError('');
        setReview(null);

        try {
            const { data } = await axios.post(
                'http://127.0.0.1:8000/github/review',
                { url: repositoryUrl },
            );
            setReview(data);
        } catch (err) {
            const detail = err.response?.data?.detail;
            setError(typeof detail === 'string' ? detail : 'Code review failed. Please try again.');
        } finally {
            setLoading(false);
        }
    }

    return (
        <section className="h-fit min-w-0 w-full self-start rounded-3xl border border-gray-200 bg-white p-5 shadow-sm sm:p-6">
            <h2 className="text-2xl font-bold text-gray-900">AI Code Review</h2>
            <p className="mt-2 text-sm text-gray-600">
                Review excerpts from up to five source files on the default branch.
            </p>
            <button
                type="button"
                onClick={runReview}
                disabled={loading}
                className="mt-5 rounded-xl bg-gray-900 px-5 py-3 text-sm font-semibold text-white hover:bg-blue-600 disabled:opacity-60"
            >
                {loading ? 'Reviewing code…' : 'Run Code Review'}
            </button>
            <div aria-live="polite" aria-busy={loading}>
                {error && <p className="mt-4 text-sm text-red-700">{error}</p>}
                {review && (
                    <div className="mt-6">
                        {review.warnings.length > 0 && (
                            <ul className="mb-4 space-y-1 text-sm text-amber-800">
                                {review.warnings.map(warning => <li key={warning}>{warning}</li>)}
                            </ul>
                        )}
                        {review.reviewed_files.length > 0 ? (
                            <details className="mb-4 text-sm text-gray-600">
                                <summary className="cursor-pointer">
                                    {review.reviewed_files.length} files reviewed on {review.branch}
                                </summary>
                                <ul className="mt-2 space-y-1 pl-4">
                                    {review.reviewed_files.map(file => (
                                        <li key={file.path} className="break-all">
                                            {file.path} · lines 1–{file.last_line} of {file.total_lines}
                                        </li>
                                    ))}
                                </ul>
                            </details>
                        ) : (
                            <p className="text-sm text-gray-600">No source excerpts were available to review.</p>
                        )}
                        {review.reviewed_files.length > 0 && review.findings.length === 0 && (
                            <p className="text-sm text-gray-600">No actionable findings in the reviewed excerpts.</p>
                        )}
                        <ul className="space-y-3">
                            {review.findings.map((finding, index) => (
                                <li
                                    key={JSON.stringify([finding.path, finding.line, finding.category, finding.tool, index])}
                                    className="rounded-xl border border-gray-200 p-4 text-sm text-gray-700"
                                >
                                    <h3 className="font-semibold text-gray-900">
                                        {categories[finding.category]} · {finding.severity} severity · {finding.tool}
                                    </h3>
                                    <p className="mt-1 break-all font-mono text-xs">
                                        {finding.path}:{finding.line}
                                    </p>
                                    <p className="mt-3">{finding.explanation}</p>
                                    <p className="mt-2"><strong>Suggested fix</strong> {finding.recommendation}</p>
                                </li>
                            ))}
                        </ul>
                    </div>
                )}
            </div>
        </section>
    );
}
