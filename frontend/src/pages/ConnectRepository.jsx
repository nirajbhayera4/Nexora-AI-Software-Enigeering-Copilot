
import { useState } from 'react';
import axios from 'axios';
import CodeReview from '../components/CodeReview';
import { Link } from 'react-router-dom';
import { FaGithub } from 'react-icons/fa';
import { ArrowLeft, Star, Code2, ExternalLink, Loader2 } from 'lucide-react';
import ArchitectureAnalysis from '../components/ArchitectureAnalysis';

function ConnectRepository() {
    const [repoUrl, setRepoUrl] = useState('');
    const [repository, setRepository] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [indexing, setIndexing] = useState(false);
    const [indexResult, setIndexResult] = useState(null);
    const [question, setQuestion] = useState('');
    const [answer, setAnswer] = useState(null);
    const [asking, setAsking] = useState(false);

    const connectRepository = async () => {
        if (!repoUrl.trim()) {
            setError('Please enter a GitHub repository URL.');
            return;
        }

        setLoading(true);
        setError('');
        setRepository(null);

        try {
            const response = await axios.get(
                'http://127.0.0.1:8000/github/repository',
                {
                    params: {
                        url: repoUrl.trim()
                    }
                }
            );

            setRepository(response.data);
        } catch (err) {
            setError(
                err.response?.data?.detail ||
                'Unable to connect to the repository. Please try again.'
            );
        } finally {
            setLoading(false);
        }
    };
    const indexRepository = async () => {
        setIndexing(true);
        setError('');
        setIndexResult(null);

        try {
            const response = await axios.post(
                'http://127.0.0.1:8000/github/index',
                null,
                {
                    params: {
                        url: repoUrl.trim()
                    }
                }
            );

            setIndexResult(response.data);

        } catch (err) {
            setError(
                err.response?.data?.detail ||
                'Repository indexing failed. Please try again.'
            );
        } finally {
            setIndexing(false);
        }
    };

    const askQuestion = async () => {
        if (!question.trim()) {
            setError('Please enter a question.');
            return;
        }

        setAsking(true);
        setError('');
        setAnswer(null);

        try {
            const response = await axios.get(
                'http://127.0.0.1:8000/github/ask',
                {
                    params: {
                        url: repoUrl.trim(),
                        question: question.trim()
                    }
                }
            );

            setAnswer(response.data);

        } catch (err) {
            setError(
                err.response?.data?.detail ||
                'Unable to generate an answer. Please try again.'
            );
        } finally {
            setAsking(false);
        }
    };



    return (
        <main className="min-h-screen bg-[#f5faf8] px-5 py-10">
            <div className="mx-auto max-w-3xl">

                <Link
                    to="/"
                    className="mb-12 inline-flex items-center gap-2 text-sm text-gray-500 hover:text-gray-900"
                >
                    <ArrowLeft size={17} />
                    Back to Home
                </Link>

                <div className="mt-16 text-center">
                    <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-gray-900 text-white">
                        <FaGithub size={32} />
                    </div>

                    <h1 className="text-4xl font-bold tracking-tight text-gray-900">
                        Connect your repository
                    </h1>

                    <p className="mt-4 text-gray-500">
                        Give Nexora access to your codebase by entering a public
                        GitHub repository URL.
                    </p>
                </div>

                <div className="mt-10 rounded-3xl border border-gray-200 bg-white p-6 shadow-sm sm:p-8">

                    <label className="mb-3 block text-sm font-semibold text-gray-700">
                        GitHub Repository URL
                    </label>

                    <div className="flex flex-col gap-3 sm:flex-row">
                        <input
                            type="url"
                            value={repoUrl}
                            onChange={(e) => setRepoUrl(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter') connectRepository();
                            }}
                            placeholder="https://github.com/owner/repository"
                            className="min-w-0 flex-1 rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                        />

                        <button
                            onClick={connectRepository}
                            disabled={loading}
                            className="flex items-center justify-center gap-2 rounded-xl bg-gray-900 px-6 py-3 text-sm font-semibold text-white transition hover:bg-blue-600 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            {loading ? (
                                <>
                                    <Loader2 size={17} className="animate-spin" />
                                    Connecting...
                                </>
                            ) : (
                                'Connect Repository'
                            )}
                        </button>
                    </div>

                    {error && (
                        <p className="mt-4 text-sm text-red-600">
                            {error}
                        </p>
                    )}

                    {repository && (
                        <div className="mt-8 rounded-2xl border border-green-200 bg-green-50/60 p-6">

                            <div className="mb-5 flex items-center gap-2 text-sm font-semibold text-green-700">
                                <span className="h-2 w-2 rounded-full bg-green-500" />
                                Repository connected successfully
                            </div>

                            <h2 className="text-2xl font-bold text-gray-900">
                                {repository.name}
                            </h2>

                            <p className="mt-1 text-sm text-gray-500">
                                {repository.full_name}
                            </p>

                            <p className="mt-4 text-sm leading-6 text-gray-600">
                                {repository.description || 'No description available.'}
                            </p>

                            <div className="mt-6 flex flex-wrap gap-5 text-sm text-gray-600">

                                <div className="flex items-center gap-2">
                                    <Code2 size={17} />
                                    {repository.language || 'Not specified'}
                                </div>

                                <div className="flex items-center gap-2">
                                    <Star size={17} />
                                    {repository.stars.toLocaleString()} stars
                                </div>

                            </div>

                            <div className="mt-6 flex flex-wrap items-center gap-4">

                                <a
                                    href={repository.url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="inline-flex items-center gap-2 text-sm font-semibold text-blue-600 hover:text-blue-800"
                                >
                                    View on GitHub
                                    <ExternalLink size={15} />
                                </a>

                                <button
                                    onClick={indexRepository}
                                    disabled={indexing}
                                    className="rounded-xl bg-gray-900 px-5 py-3 text-sm font-semibold text-white transition hover:bg-blue-600 disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                    {indexing ? 'Indexing Repository...' : 'Index Repository'}
                                </button>
                                {indexResult && (
                                    <div className="mt-6 rounded-2xl border border-green-200 bg-green-50 p-5">

                                        <div className="font-semibold text-green-700">
                                            {indexResult.message}
                                        </div>

                                        <p className="mt-2 text-sm text-gray-600">
                                            Repository: {indexResult.repository || repository.full_name}
                                        </p>

                                        <div className="mt-4 grid grid-cols-2 gap-4">

                                            <div className="rounded-xl bg-white p-4">
                                                <p className="text-sm text-gray-500">Files Processed</p>
                                                <p className="mt-1 text-2xl font-bold text-gray-900">
                                                    {indexResult.total_files ?? 0}
                                                </p>
                                            </div>

                                            <div className="rounded-xl bg-white p-4">
                                                <p className="text-sm text-gray-500">Code Chunks</p>
                                                <p className="mt-1 text-2xl font-bold text-gray-900">
                                                    {indexResult.total_chunks}
                                                </p>
                                            </div>

                                        </div>

                                    </div>
                                )}

                            </div>

                        </div>

                    )}

                </div>

                {repository && indexResult && (
                    <div className="mt-8 rounded-3xl border border-gray-200 bg-white p-6 shadow-sm sm:p-8">

                        <h2 className="text-2xl font-bold text-gray-900">
                            Ask Nexora AI
                        </h2>

                        <p className="mt-2 text-sm text-gray-500">
                            Ask questions about your repository.
                        </p>

                        <div className="mt-6 flex flex-col gap-3 sm:flex-row">
                            <input
                                type="text"
                                value={question}
                                onChange={(e) => setQuestion(e.target.value)}
                                placeholder="How does this repository work?"
                                className="min-w-0 flex-1 rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm outline-none focus:border-blue-500"
                            />

                            <button
                                onClick={askQuestion}
                                disabled={asking}
                                className="rounded-xl bg-blue-600 px-6 py-3 text-sm font-semibold text-white disabled:opacity-60"
                            >
                                {asking ? 'Thinking...' : 'Ask AI'}
                            </button>
                        </div>

                    </div>
                )}
                {answer && (
                    <div className="mt-6 rounded-2xl border border-blue-100 bg-blue-50/50 p-5">
                        <h3 className="mb-3 text-lg font-semibold text-gray-900">
                            AI Response
                        </h3>

                        <p className="whitespace-pre-wrap text-sm leading-7 text-gray-700">
                            {answer.answer}
                        </p>

                        {answer.sources?.length > 0 && (
                            <div className="mt-6 border-t border-blue-100 pt-4">
                                <h4 className="mb-3 text-sm font-semibold text-gray-900">
                                    Source Files
                                </h4>

                                <div className="space-y-2">
                                    {answer.sources.map((source, index) => (
                                        <div
                                            key={`${source.file_path}-${index}`}
                                            className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-white p-3 text-xs"
                                        >
                                            <span className="font-medium text-gray-700">
                                                {source.file_path}
                                            </span>

                                            <span className="text-gray-500">
                                                Lines {source.start_line}–{source.end_line}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                )}


                <p className="mt-6 text-center text-xs text-gray-400">
                    Currently supports public GitHub repositories.
                </p>

            </div>
        </main>
    );
}

export default ConnectRepository;
