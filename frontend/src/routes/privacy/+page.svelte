<script>
  import "$lib/styles/tokens.css";

  // Fictive placeholder values for this demo app — see the translation/
  // localization pass that replaced the earlier literal [[TOKEN]] markers
  // (issue #63's original draft) with plausible, invented details.
  const LEGAL = {
    entity: "Cashmire SAS",
    status: "Application de démonstration",
    contact: "confidentialite@cashmire.app",
    jurisdiction: "France — RGPD, sous le contrôle de la CNIL",
    controller: "Cashmire SAS",
    hosting: "hébergées en France, au sein de l'Union européenne",
    updated: "9 octobre 2026",
  };
</script>

<svelte:head>
  <title>Confidentialité et mentions légales · Cashmire</title>
  <meta
    name="description"
    content="Quelles données personnelles Cashmire collecte, pourquoi, où elles vivent et comment elles sont protégées."
  />
</svelte:head>

<main>
  <h1>Confidentialité et mentions légales</h1>

  <p>Dernière mise à jour : <time>{LEGAL.updated}</time></p>

  <h2>En bref</h2>
  <p>
    Cashmire vous permet de suivre vos dépenses et de fixer des budgets par
    catégorie. Pour cela, nous conservons votre adresse e-mail ainsi que les
    dépenses et budgets que vous créez, dans une base de données accessible
    uniquement depuis votre compte connecté.
  </p>

  <h2>Les données que nous conservons</h2>
  <ul>
    <li>
      Votre adresse e-mail et un mot de passe chiffré (jamais stocké en
      clair — voir « Comment nous protégeons vos données » ci-dessous)
    </li>
    <li>Le montant, la date et, si vous le souhaitez, une description de chaque dépense</li>
    <li>Le montant, la période et, si vous le souhaitez, un seuil d'alerte pour chaque budget</li>
    <li>La catégorie et le compte associés à chaque dépense ou budget</li>
  </ul>

  <h2>Pourquoi nous les conservons</h2>
  <p>
    Votre e-mail et votre mot de passe vous permettent de créer un compte une
    seule fois, puis de vous reconnecter pour retrouver vos propres
    données — et personne d'autre que vous ne peut y accéder. Vos dépenses et
    vos budgets alimentent les fonctionnalités de suivi : vous pouvez les
    consulter, les modifier ou les supprimer à tout moment depuis
    l'application.
  </p>

  <h2>Où vivent vos données</h2>
  <p>
    Vos données sont stockées dans une base PostgreSQL dédiée à Cashmire,
    {LEGAL.hosting}.
  </p>

  <h2>Ce qu'il se passe quand vous visitez le site</h2>
  <p>
    Si vous n'êtes pas connecté, la page d'accueil ne fait qu'une seule
    requête — vers notre propre point de terminaison de santé — qui ne
    renvoie rien vous concernant. Si vous êtes connecté, elle affiche aussi
    vos dépenses et budgets récents, uniquement les vôtres ; cette donnée
    n'est jamais transmise ailleurs. Cette page elle-même ne déclenche
    aucune requête.
  </p>
  <p>
    Comme tout serveur web, le nôtre reçoit les métadonnées de connexion
    habituelles (adresse IP, user-agent).
  </p>

  <h2>Cookies et suivi</h2>
  <p>
    Cashmire n'utilise ni outil d'analyse, ni gestionnaire de balises, ni
    pixel de suivi, ni script tiers. La connexion ou l'inscription dépose
    deux cookies internes : un cookie de session (<code>sessionid</code>,
    marqué <code>HttpOnly</code>, donc illisible par le JavaScript de la
    page) et un cookie <code>csrftoken</code> qui protège les actions
    sensibles (création, modification, suppression) contre les attaques par
    falsification de requête intersite (CSRF). Aucun de ces cookies n'est
    utilisé à des fins de suivi, d'analyse ou de publicité, et rien n'est
    transmis à un tiers.
  </p>

  <h2>Les tiers avec qui nous partageons des données</h2>
  <p>
    Cashmire ne fait appel à aucun prestataire d'analyse, d'envoi d'e-mails,
    de paiement ou de surveillance d'erreurs. Vos dépenses et vos budgets
    restent dans notre base de données, {LEGAL.hosting}.
  </p>

  <h2>Combien de temps nous les conservons</h2>
  <p>
    Vous pouvez supprimer individuellement n'importe quelle dépense ou
    budget à tout moment depuis l'application. Vos données restent
    conservées tant que vous ne les supprimez pas vous-même ou que votre
    compte n'est pas clôturé.
  </p>

  <h2>Vos droits</h2>
  <p>
    Vous disposez d'un droit d'accès, de rectification, d'effacement, de
    limitation, de portabilité et d'opposition sur vos données, ainsi que du
    droit d'introduire une réclamation auprès d'une autorité de contrôle.
    Vous pouvez déjà consulter, modifier et supprimer vos dépenses et vos
    budgets directement depuis l'application. Pour toute autre question ou
    demande, contactez-nous : <code>{LEGAL.contact}</code>.
  </p>
  <p>Juridiction applicable : {LEGAL.jurisdiction}.</p>

  <h2>Comment nous protégeons vos données</h2>
  <p>
    Votre mot de passe n'est jamais stocké en clair : il est protégé par un
    algorithme de hachage salé avant d'être enregistré. La connexion dépose
    un cookie de session <code>HttpOnly</code>, invisible pour tout script
    exécuté dans la page. La page de connexion limite les tentatives à 5 par
    minute et par adresse IP pour freiner les attaques par force brute.
  </p>
  <p>
    Chaque dépense et chaque budget est rattaché à votre compte : vous seul
    pouvez les consulter, les modifier ou les supprimer. Toute action qui
    modifie vos données est protégée contre les attaques CSRF.
  </p>

  <h2>Ce qui est prévu, et ce qui ne l'est pas encore</h2>
  <p>
    Le suivi des dépenses et des budgets, ainsi que la création de compte,
    la connexion et la déconnexion, sont pleinement fonctionnels dès
    aujourd'hui. Sont encore à venir : la suppression de compte, l'export de
    vos données, la réinitialisation de mot de passe et la vérification
    d'adresse e-mail.
  </p>

  <h2>Qui édite Cashmire</h2>
  <ul>
    <li>Éditeur : <code>{LEGAL.entity}</code></li>
    <li>Statut : <code>{LEGAL.status}</code></li>
    <li>Responsable du traitement : <code>{LEGAL.controller}</code></li>
    <li>Juridiction compétente / autorité de contrôle : <code>{LEGAL.jurisdiction}</code></li>
    <li>Contact : <code>{LEGAL.contact}</code></li>
  </ul>

  <h2>Modifications de cette page</h2>
  <p>
    Les modifications apportées à cette page sont suivies dans l'historique
    du projet. La date de dernière mise à jour en haut de page reflète le
    changement le plus récent.
  </p>

  <p><a href="/">Retour à la page d'accueil de Cashmire</a></p>
</main>

<style>
  main {
    max-width: 70ch;
    margin: 0 auto;
    padding: var(--space-2xl) var(--space-xl) var(--space-3xl);
    line-height: 1.5;
  }

  a {
    color: var(--color-primary);
  }

  a:focus-visible {
    outline: var(--focus-ring-width) solid var(--focus-ring-color);
    outline-offset: 2px;
  }

  code {
    font-size: 0.95em;
  }
</style>
