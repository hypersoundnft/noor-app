/**
 * InstagramFeed — server component powered by Behold (behold.so).
 *
 * Requires one environment variable:
 *   BEHOLD_FEED_ID  — the feed ID from your Behold dashboard
 *                     (e.g. dWnW6Eo778pkRF8j6mIC)
 *
 * Endpoint: https://feeds.behold.so/{BEHOLD_FEED_ID}
 * Images come from Behold's CDN (stable, no expiry) via post.sizes.medium.mediaUrl
 */

import Image from 'next/image';

const INSTAGRAM_HANDLE = 'noor.app_official';
const INSTAGRAM_URL = `https://www.instagram.com/${INSTAGRAM_HANDLE}/`;

const InstagramIcon = ({ className }: { className?: string }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <rect x="2" y="2" width="20" height="20" rx="5" ry="5" />
    <circle cx="12" cy="12" r="5" />
    <circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none" />
  </svg>
);

interface BeholdPost {
  id: string;
  permalink: string;
  mediaType: 'IMAGE' | 'VIDEO' | 'CAROUSEL_ALBUM';
  caption?: string;
  prunedCaption?: string;
  sizes: {
    medium: { mediaUrl: string; width: number; height: number };
  };
}

async function fetchPosts(): Promise<BeholdPost[]> {
  const feedId = process.env.BEHOLD_FEED_ID;
  if (!feedId) return [];
  try {
    const res = await fetch(`https://feeds.behold.so/${feedId}`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return [];
    const data = await res.json();
    // Behold returns either an array or { posts: [...] }
    const posts: BeholdPost[] = Array.isArray(data) ? data : (data.posts ?? []);
    return posts.slice(0, 3);
  } catch {
    return [];
  }
}

function PostCard({ post }: { post: BeholdPost }) {
  const imgUrl = post.sizes.medium.mediaUrl;
  const caption = (post.prunedCaption ?? post.caption ?? '').split('\n')[0].slice(0, 100);

  return (
    <a
      href={post.permalink}
      target="_blank"
      rel="noopener noreferrer"
      className="group relative overflow-hidden rounded-2xl bg-emerald-50 aspect-square block"
    >
      <Image
        src={imgUrl}
        alt={caption || 'Instagram post'}
        fill
        sizes="(max-width: 640px) 90vw, 33vw"
        className="object-cover transition-transform duration-500 group-hover:scale-105"
      />
      {/* Caption overlay */}
      <div className="absolute inset-0 bg-black/0 group-hover:bg-black/50 transition-colors duration-300 flex items-end p-4">
        {caption && (
          <p className="text-white text-sm leading-snug opacity-0 group-hover:opacity-100 transition-opacity duration-300 line-clamp-3">
            {caption}
          </p>
        )}
      </div>
      {post.mediaType === 'VIDEO' && (
        <span className="absolute top-3 right-3 bg-black/50 text-white text-xs px-2 py-0.5 rounded-full">
          ▶ Video
        </span>
      )}
      {post.mediaType === 'CAROUSEL_ALBUM' && (
        <span className="absolute top-3 right-3 text-white text-lg drop-shadow">⊞</span>
      )}
    </a>
  );
}

export default async function InstagramFeed() {
  const posts = await fetchPosts();

  return (
    <section className="max-w-5xl mx-auto px-6 py-20">
      {/* Header */}
      <div className="text-center mb-10">
        <div className="inline-flex items-center gap-2 bg-emerald-50 text-noor-mint border border-emerald-200 px-4 py-1.5 rounded-full text-sm font-semibold mb-4">
          <InstagramIcon className="h-3.5 w-3.5" />
          @{INSTAGRAM_HANDLE}
        </div>
        <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-noor-slate">
          Follow our journey
        </h2>
        <p className="mt-3 text-noor-muted max-w-md mx-auto">
          Daily reminders, product updates, and Islamic reflections — right on your feed.
        </p>
      </div>

      {/* Grid */}
      {posts.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-10">
          {posts.map((post) => (
            <PostCard key={post.id} post={post} />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-10">
          {[1, 2, 3].map((i) => (
            <a
              key={i}
              href={INSTAGRAM_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="group relative overflow-hidden rounded-2xl bg-emerald-50 aspect-square flex items-center justify-center hover:bg-emerald-100 transition-colors"
            >
              <InstagramIcon className="h-10 w-10 text-noor-mint opacity-40 group-hover:opacity-70 transition-opacity" />
            </a>
          ))}
        </div>
      )}

      {/* CTA */}
      <div className="flex justify-center">
        <a
          href={INSTAGRAM_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 bg-noor-mint text-white px-6 py-3.5 rounded-xl text-base font-semibold shadow-[0_4px_14px_rgba(16,185,129,0.3)] hover:bg-emerald-600 transition-colors"
        >
          <InstagramIcon className="h-4 w-4" />
          Follow @{INSTAGRAM_HANDLE}
        </a>
      </div>
    </section>
  );
}
