import { SignInButton, SignUpButton, SignedIn, SignedOut, UserButton } from "@clerk/nextjs";
import Link from "next/link";
import Head from "next/head";

export default function Home() {
  return (
    <>
      <Head>
        <title>SAGE - Strategic Agentic Generative Explainer</title>
      </Head>
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 to-slate-50">
      {/* Navigation */}
      <nav className="px-8 py-6 bg-white shadow-sm">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <div className="text-2xl font-bold text-dark">
            SAGE <span className="text-emerald-600">Financial Intelligence</span>
          </div>
          <div className="flex gap-4">
            <SignedOut>
              <SignInButton mode="modal">
                <button className="px-6 py-2 text-primary border border-primary rounded-lg hover:bg-primary hover:text-white transition-colors">
                  Sign In
                </button>
              </SignInButton>
              <SignUpButton mode="modal">
                <button className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-blue-600 transition-colors">
                  Get Started
                </button>
              </SignUpButton>
            </SignedOut>
            <SignedIn>
              <div className="flex items-center gap-4">
                <Link href="/dashboard">
                  <button className="px-6 py-2 bg-ai-accent text-white rounded-lg hover:bg-purple-700 transition-colors">
                    Go to Dashboard
                  </button>
                </Link>
                <UserButton afterSignOutUrl="/" />
              </div>
            </SignedIn>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="px-8 py-20">
        <div className="max-w-7xl mx-auto text-center">
          <h1 className="text-5xl font-bold text-dark mb-6">
            Intelligent Wealth Management
          </h1>
          <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto">
            Harness multi-agent AI orchestration for comprehensive portfolio analysis,
            retirement projections, and data-driven investment insights.
          </p>
          <div className="flex gap-6 justify-center">
            <SignedOut>
              <SignUpButton mode="modal">
                <button className="px-8 py-4 bg-ai-accent text-white text-lg rounded-lg hover:bg-purple-700 transition-colors shadow-lg">
                  Start Your Analysis
                </button>
              </SignUpButton>
            </SignedOut>
            <SignedIn>
              <Link href="/dashboard">
                <button className="px-8 py-4 bg-ai-accent text-white text-lg rounded-lg hover:bg-purple-700 transition-colors shadow-lg">
                  Open Dashboard
                </button>
              </Link>
            </SignedIn>
            <button className="px-8 py-4 border-2 border-primary text-primary text-lg rounded-lg hover:bg-primary hover:text-white transition-colors">
              Watch Demo
            </button>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="px-8 py-20 bg-white">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl font-bold text-center text-dark mb-12">
            Autonomous Agent Orchestra
          </h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            <div className="text-center p-6 rounded-xl hover:shadow-lg transition-shadow">
              <div className="text-4xl mb-4">🧠</div>
              <h3 className="text-xl font-semibold text-emerald-600 mb-2">Orchestrator</h3>
              <p className="text-gray-600">Coordinates specialized agents via SQS-based parallel processing</p>
            </div>
            <div className="text-center p-6 rounded-xl hover:shadow-lg transition-shadow">
              <div className="text-4xl mb-4">🔍</div>
              <h3 className="text-xl font-semibold text-primary mb-2">Research Agent</h3>
              <p className="text-gray-600">Browses financial news and stores insights in vector database</p>
            </div>
            <div className="text-center p-6 rounded-xl hover:shadow-lg transition-shadow">
              <div className="text-4xl mb-4">📊</div>
              <h3 className="text-xl font-semibold text-success mb-2">Analytics Agent</h3>
              <p className="text-gray-600">Generates performance metrics, risk scores, and visualizations</p>
            </div>
            <div className="text-center p-6 rounded-xl hover:shadow-lg transition-shadow">
              <div className="text-4xl mb-4">🎯</div>
              <h3 className="text-xl font-semibold text-accent mb-2">Projection Agent</h3>
              <p className="text-gray-600">Monte Carlo simulations for retirement and goal planning</p>
            </div>
          </div>
        </div>
      </section>

      {/* Benefits Section */}
      <section className="px-8 py-20 bg-gradient-to-r from-primary/10 to-ai-accent/10">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl font-bold text-center text-dark mb-12">
            Production-Ready Architecture
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="bg-white p-8 rounded-xl shadow-md">
              <div className="text-accent text-2xl mb-4">🚀</div>
              <h3 className="text-xl font-semibold mb-3">Serverless Scale</h3>
              <p className="text-gray-600">Lambda, App Runner, and Aurora Serverless v2 for cost-efficient scaling</p>
            </div>
            <div className="bg-white p-8 rounded-xl shadow-md">
              <div className="text-accent text-2xl mb-4">🔐</div>
              <h3 className="text-xl font-semibold mb-3">Enterprise Security</h3>
              <p className="text-gray-600">Clerk authentication, row-level access, and AWS security best practices</p>
            </div>
            <div className="bg-white p-8 rounded-xl shadow-md">
              <div className="text-accent text-2xl mb-4">🧬</div>
              <h3 className="text-xl font-semibold mb-3">Vector Search</h3>
              <p className="text-gray-600">S3 Vectors with SageMaker embeddings for semantic document retrieval</p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="px-8 py-20 bg-dark text-white">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl font-bold mb-6">
            Ready to Transform Your Financial Future?
          </h2>
          <p className="text-xl mb-8 opacity-90">
            Join thousands of investors using AI to optimize their portfolios
          </p>
          <SignUpButton mode="modal">
            <button className="px-8 py-4 bg-accent text-dark font-semibold text-lg rounded-lg hover:bg-yellow-500 transition-colors shadow-lg">
              Get Started Free
            </button>
          </SignUpButton>
        </div>
      </section>

      {/* Footer */}
      <footer className="px-8 py-6 bg-gray-900 text-gray-400 text-center text-sm">
        <p>© 2025 SAGE Financial Intelligence. Built by Samuel Villa-Smith.</p>
        <p className="mt-2">
          AI-generated insights are for informational purposes only. Not financial advice.
          Consult a qualified advisor before making investment decisions.
        </p>
      </footer>
    </div>
    </>
  );
}