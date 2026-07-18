const ForumActions = (() => {
  function confirmDeletion() {
    return confirm("Are you sure you want to delete this post?");
  }

  function simpleEdit(postId, currentContent) {
    const newText = prompt("Edit your post content:", currentContent || "");
    if (!newText || newText.trim() === "" || newText === currentContent) {
      return;
    }

    if (!confirm("Save changes to this post?")) {
      return;
    }

    const form = document.createElement("form");
    form.method = "POST";
    form.action = `/forum/posts/${postId}/edit#tab-wisdom-forum`;

    const input = document.createElement("input");
    input.type = "hidden";
    input.name = "content";
    input.value = newText;

    form.appendChild(input);
    document.body.appendChild(form);
    form.submit();
  }

  return { confirmDeletion, simpleEdit };
})();

window.confirmDeletion = ForumActions.confirmDeletion;
window.simpleEdit = ForumActions.simpleEdit;
