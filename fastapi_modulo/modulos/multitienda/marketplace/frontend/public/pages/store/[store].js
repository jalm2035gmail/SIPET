import Link from 'next/link';

export async function getStaticPaths() {
  return { paths: [], fallback: 'blocking' };
}

export async function getStaticProps({ params }) {
  return {
    props: {
      storeSlug: params.store,
      products: [],
    },
    revalidate: 60,
  };
}

export default function StorePage({ storeSlug, products }) {
  return (
    <main style={{ padding: 32 }}>
      <header>
        <h1>Tienda {storeSlug}</h1>
        <p>Catálogo personalizado para cada vendedor.</p>
      </header>
      <section>
        {products.length === 0 ? (
          <p>No hay productos listados aún.</p>
        ) : (
          products.map((product) => (
            <article key={product.id}>
              <Link href={`/product/${product.slug}`}>
                <a>{product.title}</a>
              </Link>
            </article>
          ))
        )}
      </section>
    </main>
  );
}
