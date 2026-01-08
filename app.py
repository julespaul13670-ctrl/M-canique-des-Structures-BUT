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
        
        self.Ra = 0
        self.Rb = 0
        self.Ma_encastrement = 0
        self.xa = 0
        self.xb = longueur
        self.type_structure = "Simple"

    def ajouter_ponctuelle(self, pos, val):
        self.charges_ponctuelles.append((pos, val))

    def ajouter_repartie(self, debut, fin, val):
        self.charges_reparties.append((debut, fin, val))

    def resoudre_statique(self, type_structure, pos_a=0, pos_b=None, unit_f="kN", unit_m="kNm"):
        self.type_structure = type_structure
        
        somme_forces_ext = 0
        somme_moments_ext_0 = 0 
        
        for pos, val in self.charges_ponctuelles:
            somme_forces_ext += val
            somme_moments_ext_0 += val * pos
            
        for debut, fin, val in self.charges_reparties:
            longueur = fin - debut
            force_res = val * longueur
            bras_levier = debut + (longueur / 2)
            somme_forces_ext += force_res
            somme_moments_ext_0 += force_res * bras_levier
            
        for pos, val in self.moments_concentres:
            somme_moments_ext_0 += val 

        # CAS 1 : Console
        if type_structure == "Console (Encastrée gauche)":
            self.xa = 0
            self.Ra = somme_forces_ext
            self.Ma_encastrement = somme_moments_ext_0
            self.Rb = 0
            return f"Réaction A: {self.Ra:.2f} {unit_f} | Moment A: {self.Ma_encastrement:.2f} {unit_m}"

        # CAS 2 : Sur 2 Appuis
        else:
            self.xa = pos_a
            self.xb = pos_b if pos_b is not None else self.L
            
            dist_appuis = self.xb - self.xa
            
            if dist_appuis == 0:
                return "Erreur : Les appuis ne peuvent pas être au même endroit."

            moment_resultante_sur_A = somme_moments_ext_0 - (somme_forces_ext * self.xa)
            self.Rb = moment_resultante_sur_A / dist_appuis
            self.Ra = somme_forces_ext - self.Rb
            self.Ma_encastrement = 0
            
            return f"Réaction A (x={self.xa}): {self.Ra:.2f} {unit_f} | Réaction B (x={self.xb}): {self.Rb:.2f} {unit_f}"

    def effort_tranchant(self, x):
        V = 0
        if self.type_structure == "Console (Encastrée gauche)":
            if x > 0: V += self.Ra
        else:
            if x > self.xa: V += self.Ra
            if x > self.xb: V += self.Rb

        for pos, val in self.charges_ponctuelles:
            if x > pos: V -= val
            
        for debut, fin, val in self.charges_reparties:
            if x > debut:
                V -= val * (min(x, fin) - debut)
        return V

    def moment_flechissant(self, x):
        M = 0
        if self.type_structure == "Console (Encastrée gauche)":
            M -= self.Ma_encastrement
            if x > 0: M += self.Ra * x
        else:
            if x > self.xa: M += self.Ra * (x - self.xa)
            if x > self.xb: M += self.Rb * (x - self.xb)

        for pos, val in self.charges_ponctuelles:
            if x > pos: M -= val * (x - pos)
        for debut, fin, val in self.charges_reparties:
            if x > debut:
                dist_active = min(x, fin) - debut
                force = val * dist_active
                bras_levier = (x - debut) - (dist_active / 2)
                M -= force * bras_levier
        return M

# --- 2. INTERFACE WEB ---
def main():
    st.set_page_config(page_title="Poutre Effort Calculateur", page_icon="🏗️", layout="wide")
    
    st.title("🏗️ Calculateur - Poutres")
    st.markdown("---")

    col_conf, col_graph = st.columns([1, 2])

    with col_conf:
        st.header("1. Configuration")
        
        # --- CHOIX UNITÉS ---
        unit_choice = st.radio("Unité de Force :", ["kN (KiloNewton)", "N (Newton)"], horizontal=True)
        u_f = "kN" if "kN" in unit_choice else "N"
        u_m = "kNm" if u_f == "kN" else "Nm"
        u_rep = "kN/m" if u_f == "kN" else "N/m"

        # --- GÉOMÉTRIE (Valeurs vides par défaut) ---
        L = st.number_input("Longueur Totale de la poutre (m)", value=0.0, step=1, min_value=0.0)
        
        if L > 0:
            poutre = PoutreCalculator(L)
            
            type_struc = st.radio("Type d'appuis", ["Sur 2 Appuis (Standard/Porte-à-faux)", "Console (Encastrée gauche)"])
            
            pos_a, pos_b = 0.0, L
            if type_struc == "Sur 2 Appuis (Standard/Porte-à-faux)":
                c1, c2 = st.columns(2)
                pos_a = c1.number_input("Position Appui A (m)", 0.0, L, 0.0, step=1)
                pos_b = c2.number_input("Position Appui B (m)", 0.0, L, 0.0, step=1)
                
                if pos_b == 0:
                    st.warning("⚠️ Attention: Position Appui B est à 0. Veuillez le placer.")
            
            st.markdown("---")
            st.header("2. Chargement")
            
            if 'charges' not in st.session_state:
                st.session_state.charges = {'dist': [], 'point': []}

            # Ajout Charges
            with st.expander(f"Ajouter Charge Répartie ({u_rep})", expanded=True):
                q_val = st.number_input(f"Valeur ({u_rep})", value=0.0, key="q_in")
                c_d, c_f = st.columns(2)
                d_val = c_d.number_input("Début (m)", value=0.0, key="d_in")
                f_val = c_f.number_input("Fin (m)", value=0.0, key="f_in")
                if st.button("Ajouter Répartie"):
                    if q_val != 0:
                        st.session_state.charges['dist'].append({'q': q_val, 'd': d_val, 'f': f_val})
                    else:
                        st.error("La valeur de la charge ne peut pas être 0.")

            with st.expander(f"Ajouter Charge Ponctuelle ({u_f})"):
                f_val_p = st.number_input(f"Force ({u_f})", value=0.0, key="fp_in")
                p_val = st.number_input("Position (m)", value=0.0, key="pp_in")
                if st.button("Ajouter Ponctuelle"):
                    if f_val_p != 0:
                        st.session_state.charges['point'].append({'F': f_val_p, 'p': p_val})
                    else:
                        st.error("La force ne peut pas être 0.")

            # Reset
            if st.button("🗑️ Effacer toutes les charges", type="primary"):
                st.session_state.charges = {'dist': [], 'point': []}

            # Liste Charges
            if st.session_state.charges['dist'] or st.session_state.charges['point']:
                st.write("### Liste des charges :")
                for i, c in enumerate(st.session_state.charges['dist']):
                    poutre.ajouter_repartie(c['d'], c['f'], c['q'])
                    st.write(f"🔹 **{i+1}.** Répartie : {c['q']} {u_rep} de {c['d']}m à {c['f']}m")
                for i, c in enumerate(st.session_state.charges['point']):
                    poutre.ajouter_ponctuelle(c['p'], c['F'])
                    st.write(f"🔻 **{i+1}.** Ponctuelle : {c['F']} {u_f} à {c['p']}m")
            else:
                st.info("Aucune charge ajoutée.")

        else:
            st.info("Veuillez commencer par entrer la longueur de la poutre.")

    # --- CALCULS ---
    with col_graph:
        if L > 0:
            # Vérification basique pour éviter calcul sur appuis confondus
            valid_calc = True
            if type_struc == "Sur 2 Appuis (Standard/Porte-à-faux)":
                if pos_a == pos_b:
                    st.error("Les appuis A et B ne peuvent pas être au même endroit.")
                    valid_calc = False

            if valid_calc:
                # Résolution
                res_text = poutre.resoudre_statique(type_struc, pos_a, pos_b, u_f, u_m)
                st.success(f"📊 RÉSULTATS : {res_text}")

                # Graphiques
                x_vals = np.linspace(0, poutre.L, 500)
                T_vals = [poutre.effort_tranchant(x) for x in x_vals]
                M_vals = [poutre.moment_flechissant(x) for x in x_vals]

                fig, (ax0, ax1, ax2) = plt.subplots(3, 1, figsize=(10, 12), gridspec_kw={'height_ratios': [1, 2, 2]})
                plt.subplots_adjust(hspace=0.4)

                # 1. Schéma
                ax0.set_title("Schéma de la structure")
                ax0.set_xlim(-0.5, L+0.5)
                ax0.set_ylim(-1.5, 2)
                ax0.axis('off')
                ax0.plot([0, L], [0, 0], color='black', linewidth=5) # Poutre

                if type_struc == "Console (Encastrée gauche)":
                    ax0.plot([0, 0], [-0.5, 0.5], color='grey', linewidth=6)
                else:
                    ax0.plot([pos_a], [-0.1], marker='^', markersize=15, color='grey')
                    ax0.text(pos_a, -0.5, "A", ha='center', fontsize=12)
                    ax0.plot([pos_b], [-0.1], marker='^', markersize=15, color='grey')
                    ax0.text(pos_b, -0.5, "B", ha='center', fontsize=12)

                # Dessin charges
                for c in st.session_state.charges['point']:
                    ax0.arrow(c['p'], 1, 0, -0.8, head_width=0.2, fc='red', ec='red')
                    ax0.text(c['p'], 1.2, f"{c['F']}{u_f}", ha='center', color='red')
                for c in st.session_state.charges['dist']:
                    ax0.fill_between([c['d'], c['f']], 0, 0.4, color='orange', alpha=0.5)
                    ax0.text((c['d']+c['f'])/2, 0.5, f"{c['q']}{u_rep}", ha='center', color='darkorange')

                # 2. Tranchant
                ax1.plot(x_vals, T_vals, 'tab:blue', lw=2)
                ax1.fill_between(x_vals, T_vals, color='tab:blue', alpha=0.3)
                ax1.set_ylabel(f'Tranchant V ({u_f})')
                ax1.grid(True, alpha=0.3)
                ax1.axhline(0, color='black', lw=1)
                
                # Annotations Max
                v_max = max(T_vals, key=abs) if T_vals else 0
                ax1.set_title(f'Effort Tranchant (Max: {v_max:.2f} {u_f})')

                # 3. Moment
                ax2.plot(x_vals, M_vals, 'tab:orange', lw=2)
                ax2.fill_between(x_vals, M_vals, color='tab:orange', alpha=0.3)
                ax2.set_ylabel(f'Moment M ({u_m})')
                ax2.set_xlabel('Position x (m)')
                ax2.grid(True, alpha=0.3)
                ax2.axhline(0, color='black', lw=1)
                ax2.invert_yaxis()
                
                m_max = max(M_vals, key=abs) if M_vals else 0
                ax2.set_title(f'Moment Fléchissant (Max: {m_max:.2f} {u_m})')

                st.pyplot(fig)
        else:
            # Image vide pour garder la mise en page
            st.write("En attente de données...")
            
if __name__ == "__main__":
    main()
