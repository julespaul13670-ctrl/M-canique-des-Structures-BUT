import streamlit as st
import matplotlib.pyplot as plt
import numpy as np

# --- 1. MOTEUR DE CALCUL ---
class PoutreCalculator:
    def __init__(self, longueur):
        self.L = longueur
        self.charges_ponctuelles = [] 
        self.charges_reparties = []
        self.moments_concentres = []
        
        # Variables pour les réactions
        self.Ra = 0
        self.Rb = 0
        self.Ma_encastrement = 0
        
        # Positions des appuis (par défaut extrémités, modifié plus tard)
        self.xa = 0
        self.xb = longueur
        self.type_structure = "Simple"

    def ajouter_ponctuelle(self, pos, val):
        self.charges_ponctuelles.append((pos, val))

    def ajouter_repartie(self, debut, fin, val):
        self.charges_reparties.append((debut, fin, val))

    def ajouter_moment(self, pos, val):
        self.moments_concentres.append((pos, val))

    def resoudre_statique(self, type_structure, pos_a=0, pos_b=None):
        self.type_structure = type_structure
        
        # Calcul des sommes globales des forces et moments par rapport à 0 (origine gauche)
        somme_forces_ext = 0
        somme_moments_ext_0 = 0 # Moment des forces ext par rapport à x=0
        
        # Contribution Charges Ponctuelles
        for pos, val in self.charges_ponctuelles:
            somme_forces_ext += val
            somme_moments_ext_0 += val * pos
            
        # Contribution Charges Réparties
        for debut, fin, val in self.charges_reparties:
            longueur = fin - debut
            force_res = val * longueur
            bras_levier = debut + (longueur / 2)
            somme_forces_ext += force_res
            somme_moments_ext_0 += force_res * bras_levier
            
        # Contribution Moments Concentrés
        for pos, val in self.moments_concentres:
            somme_moments_ext_0 += val 

        # --- CAS 1 : CONSOLE (Encastrement à gauche) ---
        if type_structure == "Console (Encastrée)":
            self.xa = 0
            self.Ra = somme_forces_ext # La réaction oppose les forces
            self.Ma_encastrement = somme_moments_ext_0 # Le moment de réaction oppose les moments
            self.Rb = 0
            return f"Réaction A: {self.Ra:.2f} kN | Moment A: {self.Ma_encastrement:.2f} kNm"

        # --- CAS 2 : SUR 2 APPUIS (Générique : Simple ou Porte-à-faux) ---
        else:
            self.xa = pos_a
            self.xb = pos_b if pos_b is not None else self.L
            
            dist_appuis = self.xb - self.xa
            
            if dist_appuis == 0:
                return "Erreur : Les appuis ne peuvent pas être au même endroit."

            # Équilibre des moments par rapport à l'appui A (pos_a)
            # Somme M_a = 0 => Rb * (xb - xa) - Somme(M_forces_ext_a) = 0
            # Note : Somme(M_forces_ext_a) = Somme_M_0 - Somme_F * xa
            
            moment_resultante_sur_A = somme_moments_ext_0 - (somme_forces_ext * self.xa)
            
            # Calcul de Rb
            self.Rb = moment_resultante_sur_A / dist_appuis
            
            # Calcul de Ra (Somme forces = 0)
            self.Ra = somme_forces_ext - self.Rb
            
            self.Ma_encastrement = 0
            
            return f"Réaction A (x={self.xa}): {self.Ra:.2f} kN | Réaction B (x={self.xb}): {self.Rb:.2f} kN"

    def effort_tranchant(self, x):
        V = 0
        
        # Réactions d'appuis (forces vers le haut donc négatives dans V si on regarde à gauche convention RDM classique V + dM/dx ..)
        # Simplification : On fait Somme des forces à gauche de la coupure.
        # Force vers le haut (+), Force vers le bas (-).
        # V(x) = Somme F_verticales_gauche
        
        # Si Encastré
        if self.type_structure == "Console (Encastrée)":
            if x > 0: V += self.Ra # Ra vers le haut (supposé compenser charge vers le bas)
            # Note : Ra calculé précédemment est égal à la charge, donc vers le haut.
            
        # Si Appuis
        else:
            if x > self.xa: V += self.Ra # Réaction A vers le haut
            if x > self.xb: V += self.Rb # Réaction B vers le haut

        # Charges externes (vers le bas = négatives)
        for pos, val in self.charges_ponctuelles:
            if x > pos: V -= val
            
        for debut, fin, val in self.charges_reparties:
            if x > debut:
                # Charge répartie vers le bas
                V -= val * (min(x, fin) - debut)
                
        return V

    def moment_flechissant(self, x):
        M = 0
        
        # Moment dû aux réactions (Positif = fait sourire la poutre)
        
        # Si Encastré (Attention au signe du moment d'encastrement)
        if self.type_structure == "Console (Encastrée)":
            # Le moment d'encastrement calculé réagit aux charges.
            # M(x) initial à x=0 est -M_encastrement
            M -= self.Ma_encastrement
            if x > 0: M += self.Ra * x
            
        # Si Appuis
        else:
            if x > self.xa: M += self.Ra * (x - self.xa)
            if x > self.xb: M += self.Rb * (x - self.xb)

        # Moments dus aux charges externes
        for pos, val in self.charges_ponctuelles:
            if x > pos: M -= val * (x - pos)
            
        for debut, fin, val in self.charges_reparties:
            if x > debut:
                dist_active = min(x, fin) - debut
                force = val * dist_active
                bras_levier = (x - debut) - (dist_active / 2) # Distance entre x et le centre de la charge active
                M -= force * bras_levier
                
        for pos, val in self.moments_concentres:
            if x > pos: M += val # Convention : moment horaire positif
            
        return M

# --- 2. INTERFACE WEB ---
def main():
    st.set_page_config(page_title="RDM Calculator Pro", page_icon="🏗️", layout="wide")
    
    st.title("🏗️ Calculateur de Poutre (Porte-à-faux supporté)")
    st.markdown("---")

    col_conf, col_graph = st.columns([1, 2])

    with col_conf:
        st.header("1. Configuration")
        
        L = st.number_input("Longueur Totale (m)", value=6.0, step=0.5)
        poutre = PoutreCalculator(L)
        
        type_struc = st.radio("Type de structure", ["Sur 2 Appuis (Standard/Porte-à-faux)", "Console (Encastrée gauche)"])
        
        pos_a, pos_b = 0, L
        if type_struc == "Sur 2 Appuis (Standard/Porte-à-faux)":
            c1, c2 = st.columns(2)
            pos_a = c1.number_input("Position Appui A (m)", 0.0, L, 0.0, step=0.5)
            pos_b = c2.number_input("Position Appui B (m)", 0.0, L, 4.0, step=0.5) # Par défaut à 4m pour tester porte-à-faux
            
            if pos_a >= pos_b:
                st.error("L'appui A doit être à gauche de l'appui B.")

        st.header("2. Chargement")
        
        # Gestion dynamique des charges via Session State pour éviter rechargement
        if 'charges' not in st.session_state:
            st.session_state.charges = {'dist': [], 'point': []}

        with st.expander("Ajouter Charge Répartie", expanded=True):
            q_val = st.number_input("Valeur (kN/m)", value=5.0)
            c_d, c_f = st.columns(2)
            d_val = c_d.number_input("Début (m)", value=0.0)
            f_val = c_f.number_input("Fin (m)", value=4.0) # Par défaut sur la travée centrale
            if st.button("Ajouter Répartie"):
                st.session_state.charges['dist'].append({'q': q_val, 'd': d_val, 'f': f_val})

        with st.expander("Ajouter Charge Ponctuelle"):
            f_val = st.number_input("Force (kN)", value=10.0)
            p_val = st.number_input("Position (m)", value=L) # Par défaut au bout
            if st.button("Ajouter Ponctuelle"):
                st.session_state.charges['point'].append({'F': f_val, 'p': p_val})

        # Bouton Reset
        if st.button("Effacer toutes les charges", type="primary"):
            st.session_state.charges = {'dist': [], 'point': []}

        # Application des charges au moteur
        st.write("### Liste des charges :")
        for c in st.session_state.charges['dist']:
            poutre.ajouter_repartie(c['d'], c['f'], c['q'])
            st.write(f"- Répartie : {c['q']} kN/m de {c['d']}m à {c['f']}m")
            
        for c in st.session_state.charges['point']:
            poutre.ajouter_ponctuelle(c['p'], c['F'])
            st.write(f"- Ponctuelle : {c['F']} kN à {c['p']}m")

    # --- CALCULS ET GRAPHIQUES ---
    with col_graph:
        # Résolution
        if type_struc == "Sur 2 Appuis (Standard/Porte-à-faux)":
            res_text = poutre.resoudre_statique(type_struc, pos_a, pos_b)
        else:
            res_text = poutre.resoudre_statique(type_struc)
            
        st.success(f"📊 {res_text}")

        # Génération des points
        x_vals = np.linspace(0, poutre.L, 500)
        T_vals = [poutre.effort_tranchant(x) for x in x_vals]
        M_vals = [poutre.moment_flechissant(x) for x in x_vals]

        # Dessin Matplotlib
        fig, (ax0, ax1, ax2) = plt.subplots(3, 1, figsize=(10, 12), gridspec_kw={'height_ratios': [1, 2, 2]})
        plt.subplots_adjust(hspace=0.3)

        # 1. Schéma de la Poutre (Visualisation physique)
        ax0.set_title("Schéma de la Poutre")
        ax0.set_xlim(-0.5, L+0.5)
        ax0.set_ylim(-1, 2)
        ax0.axis('off')
        
        # Poutre
        ax0.plot([0, L], [0, 0], color='black', linewidth=5)
        
        # Appuis
        if type_struc == "Console (Encastrée)":
            ax0.plot([0, 0], [-0.5, 0.5], color='grey', linewidth=5) # Mur
        else:
            # Triangle Appui A
            ax0.plot([pos_a], [-0.1], marker='^', markersize=15, color='grey')
            ax0.text(pos_a, -0.4, "A", ha='center')
            # Triangle Appui B
            ax0.plot([pos_b], [-0.1], marker='^', markersize=15, color='grey')
            ax0.text(pos_b, -0.4, "B", ha='center')

        # Charges (Visualisation simplifiée)
        for c in st.session_state.charges['point']:
            ax0.arrow(c['p'], 1, 0, -0.8, head_width=0.2, head_length=0.2, fc='red', ec='red')
            ax0.text(c['p'], 1.1, f"{c['F']}kN", ha='center', color='red')
            
        for c in st.session_state.charges['dist']:
            ax0.fill_between([c['d'], c['f']], 0, 0.3, color='orange', alpha=0.5)
            ax0.text((c['d']+c['f'])/2, 0.4, f"{c['q']}kN/m", ha='center', color='darkorange')


        # 2. Effort Tranchant
        ax1.plot(x_vals, T_vals, 'tab:blue', lw=2)
        ax1.fill_between(x_vals, T_vals, color='tab:blue', alpha=0.3)
        ax1.set_ylabel('Effort Tranchant V (kN)')
        ax1.set_title('Diagramme Effort Tranchant')
        ax1.grid(True, alpha=0.3)
        ax1.axhline(0, color='black', lw=1)

        # 3. Moment Fléchissant
        ax2.plot(x_vals, M_vals, 'tab:orange', lw=2)
        ax2.fill_between(x_vals, M_vals, color='tab:orange', alpha=0.3)
        ax2.set_ylabel('Moment Fléchissant M (kNm)')
        ax2.set_xlabel('Position x (m)')
        ax2.set_title('Diagramme Moment Fléchissant')
        ax2.grid(True, alpha=0.3)
        ax2.axhline(0, color='black', lw=1)
        ax2.invert_yaxis() # Convention ingénieur civil

        st.pyplot(fig)

if __name__ == "__main__":
    main()
