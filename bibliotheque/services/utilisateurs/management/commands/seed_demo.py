"""
Peuple la base avec des données de démonstration DIT Library.

Usage:
    python manage.py seed_demo
    python manage.py seed_demo --clear
"""
import json
from datetime import timedelta
from io import BytesIO
from urllib.parse import quote
from urllib.request import urlopen, Request

from django.core.files import File
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.text import slugify

from services.livres.models import Book, Category, Favorite
from services.emprunts.models import Loan, Reservation
from services.notifications.models import Notification

User = get_user_model()

DEMO_PASSWORD = "Dit2026!"

# Couvertures Open Library (ISBN réels) pour la démo visuelle
BOOK_COVER_ISBN = {
    "Deep Learning avec Python": "9781617294433",
    "Clean Code": "9780132350884",
    "Introduction aux Réseaux Neuronaux": "9780262035613",
    "Économie Internationale": "9780132147475",
    "Les Misérables": "9782070413084",
    "Physique Quantique pour Tous": "9782360003293",
    "Marketing Digital & Stratégie": "9782746087430",
    "Droit du numérique en Afrique": "9782340045678",
    "The Lean Startup": "9781449305178",
    "Systèmes distribués": "9781449373326",
    "L'Intelligence artificielle en Afrique": "9782340048907",
    "Python pour la Data Science": "9781491912058",
    "Design Patterns": "9780201633610",
    "Penser, vite et lent": "9780374533557",
    "L'Étranger": "9782070360024",
    "Une brève histoire du temps": "9780553380163",
    "Blockchain et crypto-actifs": "9781492031499",
    "Gestion de projet agile": "9782746090160",
    "Le Petit Prince": "9782070612758",
    "1984": "9782070368228",
    "Harry Potter à l'école des sorciers": "9782070546008",
    "Sapiens : une brève histoire de l'humanité": "9782070659013",
    "Zero to One": "9782756027693",
    "The Pragmatic Programmer": "9780135957059",
    "JavaScript: The Good Parts": "9780596517747",
    "Clean Architecture": "9780134494166",
    "Introduction à l'algorithmique": "9782729831359",
    "Réseaux informatiques": "9782746084205",
    "Cybersécurité : guide pratique": "9782409023456",
    "Docker — Pratique des conteneurs": "9782412041924",
    "Kubernetes in Action": "9781617294648",
    "Factfulness": "9781473637460",
    "Microéconomie": "9782133813958",
    "L'Art de la guerre": "9782253006320",
    "Projet Phoenix": "9782756022094",
    "Database System Concepts": "9780073523323",
    "Introduction to Machine Learning": "9780262046308",
    "Comptabilité générale": "9782100811218",
    "Droit des affaires OHADA": "9782340012345",
    "Entrepreneuriat en Afrique": "9782340023456",
    "Communication professionnelle": "9782100745678",
    "Statistiques appliquées": "9782100812345",
    "Éthique et société numérique": "9782130812345",
}


class Command(BaseCommand):
    help = "Insère des utilisateurs, livres, emprunts et notifications de démonstration."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Supprime les données de démo avant de réinsérer.",
        )
        parser.add_argument(
            "--refresh-covers",
            action="store_true",
            help="Re-télécharge les couvertures manquantes (sans tout supprimer).",
        )

    def handle(self, *args, **options):
        refresh = options.get("refresh_covers", False)
        if refresh and not options["clear"]:
            books = list(Book.objects.filter(isbn__startswith="978-DIT-").order_by("title"))
            self._seed_book_covers(books, force=True)
            self.stdout.write(self.style.SUCCESS("\n[OK] Couvertures mises a jour.\n"))
            return
        if options["clear"]:
            self._clear_demo()
        self._seed_categories()
        users = self._seed_users()
        books = self._seed_books()
        self._seed_book_covers(books, force=refresh)
        self._seed_loans(users, books)
        self._seed_favorites(users, books)
        self._seed_notifications(users)
        self.stdout.write(self.style.SUCCESS("\n[OK] Donnees de demo pretes.\n"))
        self._print_credentials(users)

    def _clear_demo(self):
        self.stdout.write("Suppression des données de démo…")
        Notification.objects.all().delete()
        Favorite.objects.all().delete()
        Loan.objects.all().delete()
        Reservation.objects.all().delete()
        Book.objects.filter(isbn__startswith="978-DIT-").delete()
        Category.objects.filter(slug__in=[
            "informatique", "economie", "litterature", "sciences",
            "technologie", "droit", "management",
        ]).delete()
        User.objects.filter(email__endswith="@dit.sn").delete()

    def _seed_categories(self):
        cats = [
            ("Informatique", "Livres sur la programmation, l'IA et les réseaux."),
            ("Économie", "Macroéconomie, finance et commerce international."),
            ("Littérature", "Romans, essais et classiques."),
            ("Sciences", "Physique, biologie et sciences naturelles."),
            ("Technologie", "Innovation, numérique et entrepreneuriat."),
            ("Droit", "Droit des affaires et droit numérique."),
            ("Management", "Leadership, gestion de projet et RH."),
        ]
        for name, desc in cats:
            Category.objects.get_or_create(
                slug=slugify(name),
                defaults={"name": name, "description": desc},
            )
        self.stdout.write(f"  - {len(cats)} categories")

    def _seed_users(self):
        profiles = [
            ("admin@dit.sn", "Mamadou", "Diallo", User.Role.ADMIN, True, True, None),
            ("bibliotheque@dit.sn", "Fatou", "Sow", User.Role.STAFF, True, False, "Bibliothèque"),
            ("prof.kane@dit.sn", "Ibrahima", "Kane", User.Role.TEACHER, False, False, "Informatique"),
            ("aminata.diop@dit.sn", "Aminata", "Diop", User.Role.STUDENT, False, False, "Génie Logiciel"),
            ("ousmane.fall@dit.sn", "Ousmane", "Fall", User.Role.STUDENT, False, False, "Data Science"),
            ("marieme.ndiaye@dit.sn", "Marième", "Ndiaye", User.Role.STUDENT, False, False, "Cybersécurité"),
        ]
        users = {}
        for email, first, last, role, is_staff, is_super, dept in profiles:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "role": role,
                    "is_staff": is_staff,
                    "is_superuser": is_super,
                    "department": dept or "",
                    "student_id": f"DIT-{slugify(first)[:3].upper()}001" if role == User.Role.STUDENT else "",
                    "phone": "+221 77 000 00 00",
                    "bio": f"Membre DIT Library – {dept or role}.",
                },
            )
            if created or options_reset_password(user):
                user.set_password(DEMO_PASSWORD)
                user.save()
            users[email] = user
        self.stdout.write(f"  - {len(users)} utilisateurs")
        return users

    def _seed_books(self):
        cat = {c.slug: c for c in Category.objects.all()}
        catalog = [
            ("Deep Learning avec Python", "François Chollet", "informatique", 2018, 3, 2,
             "Introduction pratique au deep learning avec Keras et TensorFlow."),
            ("Clean Code", "Robert C. Martin", "informatique", 2008, 2, 2,
             "Bonnes pratiques pour écrire du code maintenable."),
            ("Introduction aux Réseaux Neuronaux", "Michael Nielsen", "informatique", 2015, 2, 1,
             "Réseaux de neurones expliqués simplement, en ligne et en livre."),
            ("Économie Internationale", "Paul Krugman", "economie", 2014, 2, 2,
             "Théories du commerce international et politiques économiques."),
            ("Les Misérables", "Victor Hugo", "litterature", 1862, 1, 0,
             "Chef-d'œuvre de la littérature française – édition intégrale."),
            ("Physique Quantique pour Tous", "Carlo Rovelli", "sciences", 2016, 2, 2,
             "Vulgarisation accessible de la physique quantique."),
            ("Marketing Digital & Stratégie", "Stéphane Truphème", "technologie", 2020, 3, 3,
             "Stratégies digitales pour les entreprises africaines."),
            ("Droit du numérique en Afrique", "Awa Ly", "droit", 2022, 2, 1,
             "Cadre juridique des données personnelles et e-commerce."),
            ("The Lean Startup", "Eric Ries", "management", 2011, 2, 2,
             "Méthodologie lean pour lancer des startups."),
            ("Systèmes distribués", "Martin Kleppmann", "informatique", 2017, 2, 1,
             "Conception de systèmes fiables à grande échelle."),
            ("L'Intelligence artificielle en Afrique", "Collectif DIT", "technologie", 2024, 4, 4,
             "Études de cas IA au Sénégal et en Afrique de l'Ouest."),
            ("Python pour la Data Science", "Jake VanderPlas", "informatique", 2016, 3, 2,
             "NumPy, Pandas, Matplotlib et Scikit-learn."),
            ("Design Patterns", "Gang of Four", "informatique", 1994, 2, 2,
             "23 modèles de conception pour la programmation orientée objet."),
            ("Penser, vite et lent", "Daniel Kahneman", "economie", 2011, 2, 1,
             "Psychologie cognitive et prise de décision économique."),
            ("L'Étranger", "Albert Camus", "litterature", 1942, 3, 3,
             "Roman existentialiste — classique du programme."),
            ("Une brève histoire du temps", "Stephen Hawking", "sciences", 1988, 2, 2,
             "Cosmologie accessible au grand public."),
            ("Blockchain et crypto-actifs", "Antonopoulos", "technologie", 2019, 2, 2,
             "Technologies décentralisées et applications."),
            ("Gestion de projet agile", "Ken Schwaber", "management", 2016, 3, 3,
             "Scrum, Kanban et delivery en équipe."),
            ("Le Petit Prince", "Antoine de Saint-Exupéry", "litterature", 1943, 4, 3,
             "Conte philosophique et poétique, classique mondial."),
            ("1984", "George Orwell", "litterature", 1949, 3, 2,
             "Roman dystopique sur la surveillance et la liberté."),
            ("Harry Potter à l'école des sorciers", "J.K. Rowling", "litterature", 1997, 5, 4,
             "Premier tome de la saga fantasy la plus populaire."),
            ("Sapiens : une brève histoire de l'humanité", "Yuval Noah Harari", "sciences", 2011, 3, 2,
             "Histoire de l'humanité et des révolutions cognitives."),
            ("Zero to One", "Peter Thiel", "management", 2014, 2, 2,
             "Notes sur les startups et la construction du futur."),
            ("The Pragmatic Programmer", "David Thomas", "informatique", 2019, 3, 3,
             "Parcours du développeur professionnel."),
            ("JavaScript: The Good Parts", "Douglas Crockford", "informatique", 2008, 2, 2,
             "Les meilleures pratiques JavaScript."),
            ("Clean Architecture", "Robert C. Martin", "informatique", 2017, 2, 2,
             "Structure des applications logicielles maintenables."),
            ("Introduction à l'algorithmique", "Thomas H. Cormen", "informatique", 2009, 4, 3,
             "Algorithmes et structures de données — référence."),
            ("Réseaux informatiques", "Andrew Tanenbaum", "informatique", 2011, 3, 2,
             "Protocoles, TCP/IP et architecture réseau."),
            ("Cybersécurité : guide pratique", "Bruce Schneier", "informatique", 2020, 3, 3,
             "Sécurité des systèmes et protection des données."),
            ("Docker — Pratique des conteneurs", "Jérôme Petazzoni", "technologie", 2018, 3, 3,
             "Conteneurisation et déploiement moderne."),
            ("Kubernetes in Action", "Marko Lukša", "informatique", 2018, 2, 2,
             "Orchestration de conteneurs en production."),
            ("Factfulness", "Hans Rosling", "sciences", 2018, 2, 2,
             "Dix raisons de voir le monde avec optimisme."),
            ("Microéconomie", "Paul Samuelson", "economie", 2010, 3, 2,
             "Principes fondamentaux de l'économie."),
            ("L'Art de la guerre", "Sun Tzu", "management", 2015, 2, 2,
             "Stratégie et leadership — texte classique."),
            ("Projet Phoenix", "Gene Kim", "technologie", 2018, 3, 2,
             "DevOps et transformation IT dans une entreprise."),
            ("Database System Concepts", "Abraham Silberschatz", "informatique", 2019, 2, 1,
             "Bases de données relationnelles et NoSQL."),
            ("Introduction to Machine Learning", "Ethem Alpaydin", "informatique", 2020, 3, 3,
             "Apprentissage supervisé et non supervisé."),
            ("Comptabilité générale", "Collectif DIT", "economie", 2021, 4, 4,
             "Comptabilité pour étudiants en gestion."),
            ("Droit des affaires OHADA", "Collectif juridique", "droit", 2023, 2, 2,
             "Cadre juridique des entreprises en Afrique."),
            ("Entrepreneuriat en Afrique", "Moussa Diop", "management", 2022, 3, 3,
             "Créer et développer une startup locale."),
            ("Communication professionnelle", "Marie Faye", "management", 2019, 3, 3,
             "Prise de parole et rédaction professionnelle."),
            ("Statistiques appliquées", "Collectif DIT", "sciences", 2020, 3, 2,
             "Statistiques pour la data science et la recherche."),
            ("Éthique et société numérique", "Collectif DIT", "droit", 2024, 2, 2,
             "Enjeux éthiques de l'IA et du numérique."),
        ]
        books = []
        for i, (title, author, slug, year, total, avail, desc) in enumerate(catalog, start=1):
            isbn = f"978-DIT-{i:05d}-{i % 10}"
            book, _ = Book.objects.get_or_create(
                isbn=isbn,
                defaults={
                    "title": title,
                    "author": author,
                    "category": cat.get(slug),
                    "year": year,
                    "total_copies": total,
                    "available_copies": avail,
                    "description": desc,
                    "publisher": "DIT Press" if "DIT" in author else "Éditions standard",
                    "pages": 200 + i * 37,
                    "language": "Français",
                    "keywords": f"{slug}, dit, bibliothèque",
                    "location": "DIT Campus – Zone A",
                    "call_number": f"{slug[:3].upper()}-{i:03d}",
                },
            )
            books.append(book)
        self.stdout.write(f"  - {len(books)} livres")
        return books

    def _download_cover_bytes(self, url):
        req = Request(url, headers={"User-Agent": "DIT-Library-Demo/1.0"})
        with urlopen(req, timeout=15) as resp:
            data = resp.read()
        return data if len(data) >= 500 else None

    def _cover_from_openlibrary_search(self, title):
        """Recherche Open Library par titre si pas d'ISBN connu."""
        try:
            search_url = (
                "https://openlibrary.org/search.json?"
                f"title={quote(title)}&limit=1&fields=cover_i,isbn"
            )
            req = Request(search_url, headers={"User-Agent": "DIT-Library-Demo/1.0"})
            with urlopen(req, timeout=12) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            docs = payload.get("docs") or []
            if not docs:
                return None
            doc = docs[0]
            if doc.get("cover_i"):
                return self._download_cover_bytes(
                    f"https://covers.openlibrary.org/b/id/{doc['cover_i']}-L.jpg"
                )
            for isbn in doc.get("isbn") or []:
                data = self._download_cover_bytes(
                    f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"
                )
                if data:
                    return data
        except Exception:
            return None
        return None

    def _seed_book_covers(self, books, force=False):
        """Télécharge les couvertures depuis Open Library (ISBN ou recherche titre)."""
        ok = 0
        skipped = 0
        for book in books:
            if book.cover and not force:
                skipped += 1
                continue
            data = None
            isbn = BOOK_COVER_ISBN.get(book.title)
            if isbn:
                try:
                    data = self._download_cover_bytes(
                        f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"
                    )
                except Exception:
                    data = None
            if not data:
                data = self._cover_from_openlibrary_search(book.title)
            if data:
                book.cover.save(f"cover_{book.pk or book.id}.jpg", File(BytesIO(data)), save=True)
                ok += 1
        self.stdout.write(f"  - {ok} couvertures ({skipped} deja presentes)")

    def _seed_loans(self, users, books):
        student = users["aminata.diop@dit.sn"]
        student2 = users["ousmane.fall@dit.sn"]
        today = timezone.now().date()

        loans_data = [
            (student, books[0], today - timedelta(days=21), today - timedelta(days=7), Loan.Status.ACTIVE, 1),
            (student, books[3], today - timedelta(days=5), today + timedelta(days=9), Loan.Status.ACTIVE, 0),
            (student, books[4], today - timedelta(days=28), today + timedelta(days=3), Loan.Status.RENEWED, 2),
            (student2, books[1], today - timedelta(days=3), today + timedelta(days=11), Loan.Status.ACTIVE, 0),
            (student, books[2], today - timedelta(days=60), today - timedelta(days=46), Loan.Status.RETURNED, 0),
            (student2, books[9], today - timedelta(days=90), today - timedelta(days=76), Loan.Status.RETURNED, 0),
        ]

        for user, book, borrowed, due, status, renewals in loans_data:
            loan, created = Loan.objects.get_or_create(
                user=user,
                book=book,
                borrowed_at=borrowed,
                defaults={
                    "due_date": due,
                    "status": status,
                    "renewal_count": renewals,
                },
            )
            if created and status == Loan.Status.RETURNED:
                loan.returned_at = due + timedelta(days=2)
                loan.save(update_fields=["returned_at"])

        # Réservation en attente (livre indisponible)
        Reservation.objects.get_or_create(
            user=student2,
            book=books[4],
            status=Reservation.Status.PENDING,
        )

        self.stdout.write(f"  - {Loan.objects.count()} emprunts, {Reservation.objects.count()} reservations")

    def _seed_favorites(self, users, books):
        student = users["aminata.diop@dit.sn"]
        for book in books[6:9]:
            Favorite.objects.get_or_create(user=student, book=book)
        self.stdout.write(f"  - {Favorite.objects.count()} favoris")

    def _seed_notifications(self, users):
        student = users["aminata.diop@dit.sn"]
        items = [
            (Notification.Type.LOAN_OVERDUE, "Retard : Deep Learning avec Python",
             "Votre emprunt est en retard de 7 jours.", "/loans/"),
            (Notification.Type.LOAN_REMINDER, "Retour prévu : Économie Internationale",
             "À retourner dans 9 jours.", "/loans/"),
            (Notification.Type.RECOMMENDATION, "Nouvelles recommandations",
             "Découvrez Python pour la Data Science et Systèmes distribués.", "/recommendations/"),
            (Notification.Type.RESERVATION, "Réservation enregistrée",
             "Vous serez notifié quand Les Misérables sera disponible.", "/loans/"),
        ]
        for ntype, title, msg, link in items:
            Notification.objects.get_or_create(
                user=student,
                title=title,
                defaults={"type": ntype, "message": msg, "link": link},
            )
        self.stdout.write(f"  - {Notification.objects.count()} notifications")

    def _print_credentials(self, users):
        self.stdout.write(self.style.WARNING("\n-- Comptes de test (mot de passe : Dit2026!) --\n"))
        for email, user in users.items():
            self.stdout.write(f"  {user.get_role_display():14}  {email}")
        self.stdout.write("\n  Admin Django : admin@dit.sn / Dit2026!")
        self.stdout.write("  URL          : http://127.0.0.1:8000/login/\n")


def options_reset_password(user):
    """Toujours réinitialiser le mot de passe des comptes @dit.sn en démo."""
    return user.email.endswith("@dit.sn")
