// --- library browser --------------------------------------------------------

function currentCategory() {
  return state.categories.find((c) => c.slug === state.category);
}

function articlesIn(slug) {
  return state.articles.filter((a) => a.category === slug);
}

function renderCategories() {
  const host = $('categories');
  host.innerHTML = '';
  for (const category of state.categories) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = category.count ? 'cat' : 'cat empty';
    button.setAttribute('aria-pressed', String(category.slug === state.category));
    button.innerHTML = `${category.icon} ${escapeHtml(category.label)}`
      + `<span class="count">${category.count}</span>`;
    button.addEventListener('click', () => {
      state.category = category.slug;
      renderCategories();
      renderArticleGrid();
    });
    host.appendChild(button);
  }
  const current = currentCategory();
  $('categoryBlurb').textContent = current ? current.blurb : '';
}

function renderArticleGrid() {
  const host = $('articleGrid');
  host.innerHTML = '';
  const list = articlesIn(state.category);
  if (!list.length) {
    const note = document.createElement('p');
    note.className = 'empty-note';
    note.textContent = '這個類別還在補充文章，先看看其他類別吧。';
    host.appendChild(note);
    return;
  }
  for (const art of list) {
    const card = document.createElement('button');
    card.type = 'button';
    card.className = 'article-card';
    card.setAttribute('role', 'listitem');
    if (art.id === state.articleId) card.setAttribute('aria-current', 'true');
    const name = document.createElement('div');
    name.className = 'name';
    name.textContent = art.displayTitle;
    const who = document.createElement('div');
    who.className = 'who';
    who.textContent = `${art.author}・${art.genre}`;
    card.append(name, who);
    card.addEventListener('click', () => {
      state.articleId = art.id;
      restart();
    });
    host.appendChild(card);
  }
}
